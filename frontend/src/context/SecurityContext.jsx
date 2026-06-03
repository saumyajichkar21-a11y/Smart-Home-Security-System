import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

const SecurityContext = createContext(null);

const BASE_URL   = 'http://localhost:5000';
const STREAM_URL = 'http://localhost:5000/stream';

export const SecurityProvider = ({ children }) => {
    const [state, setState] = useState({
        timestamp       : new Date().toISOString(),
        system_status   : 'DISARMED',
        threat_level    : 'LOW',
        sensors         : { pir_motion: 0, mq2_gas_ppm: 120, window_intrusion: 0 },
        ai_analysis     : {
            face_detected      : false,
            verdict            : 'SCANNING',
            person_name        : '',
            confidence_score   : 0,
            bounding_box       : null,
            latest_snapshot_url: null,
        },
        hardware_outputs: { relay_state: 0, buzzer_siren: 0, warning_led: 0 },
        events          : [],
        source          : 'ESP32-CAM',
        esp32_online    : false,
    });

    const [connectionStatus, setConnectionStatus] = useState('disconnected');
    const [gasHistory,       setGasHistory]       = useState([]);
    const intervalRef     = useRef(null);
    const prevStateRef    = useRef(state);

    const addEvent = useCallback((event) => {
        setState(prev => ({
            ...prev,
            events: [event, ...prev.events].slice(0, 50),
        }));
    }, []);

    // No WebSocket — Flask uses REST. Commands just log for now.
    const sendCommand = useCallback((action) => {
        console.log('[Sentinel] Command:', action, '(Flask server has no arm/disarm endpoint)');
        // Optimistically update UI
        if (action === 'arm' || action === 'ARM') {
            setState(prev => ({ ...prev, system_status: 'ARMED' }));
        } else if (action === 'disarm' || action === 'DISARM') {
            setState(prev => ({
                ...prev,
                system_status   : 'DISARMED',
                threat_level    : 'LOW',
                hardware_outputs: { relay_state: 0, buzzer_siren: 0, warning_led: 0 },
            }));
        } else if (action === 'reset_alert' || action === 'RESET_ALARM') {
            setState(prev => ({
                ...prev,
                threat_level    : 'LOW',
                hardware_outputs: { relay_state: 0, buzzer_siren: 0, warning_led: 0 },
                ai_analysis     : { ...prev.ai_analysis, verdict: 'SCANNING', face_detected: false, confidence_score: 0 },
            }));
        }
    }, []);

    const poll = useCallback(async () => {
    try {
        const res  = await fetch(`${BASE_URL}/status`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const verdict      = data.result       || 'SCANNING';
        const person_name  = data.person_name  || '';
        const face_detected = data.face_detected ?? (verdict === 'KNOWN' || verdict === 'UNKNOWN' || verdict === 'UNKNOWN_ARMED');
        const confidence   = data.confidence_score ?? (
            verdict === 'KNOWN'         ? 0.92 :
            verdict === 'UNKNOWN'       ? 0.75 :
            verdict === 'UNKNOWN_ARMED' ? 0.88 : 0
        );
        const threat_level       = data.threat_level       || 'LOW';
        const hardware_outputs   = data.hardware_outputs   || { relay_state: 0, buzzer_siren: 0, warning_led: 0 };
        const sensors            = data.sensors            || { pir_motion: 0, mq2_gas_ppm: 120, window_intrusion: 0 };

        setState(prev => {
            const newEvents = [];

            if (verdict !== prev.ai_analysis?.verdict) {
                const name     = person_name ? ` — ${person_name}` : '';
                const severity = verdict === 'UNKNOWN_ARMED' ? 'danger'
                               : verdict === 'UNKNOWN'       ? 'warning' : 'info';
                newEvents.push({
                    id       : Date.now() + Math.random(),
                    timestamp: new Date().toISOString(),
                    type     : 'ai',
                    message  : `Face recognition: ${verdict}${name}`,
                    severity,
                });
            }

            if (threat_level !== prev.threat_level) {
                newEvents.push({
                    id       : Date.now() + Math.random(),
                    timestamp: new Date().toISOString(),
                    type     : 'status',
                    message  : `Threat level: ${threat_level}`,
                    severity : threat_level === 'CRITICAL' || threat_level === 'HIGH' ? 'danger'
                             : threat_level === 'MEDIUM' ? 'warning' : 'info',
                });
            }

            if (hardware_outputs.buzzer_siren && !prev.hardware_outputs?.buzzer_siren) {
                newEvents.push({
                    id       : Date.now() + Math.random(),
                    timestamp: new Date().toISOString(),
                    type     : 'hardware',
                    message  : 'Siren activated',
                    severity : 'danger',
                });
            }

            if (sensors.pir_motion && !prev.sensors?.pir_motion) {
                newEvents.push({
                    id       : Date.now() + Math.random(),
                    timestamp: new Date().toISOString(),
                    type     : 'sensor',
                    message  : 'Motion detected by PIR sensor',
                    severity : 'warning',
                });
            }

            if (sensors.window_intrusion && !prev.sensors?.window_intrusion) {
                newEvents.push({
                    id       : Date.now() + Math.random(),
                    timestamp: new Date().toISOString(),
                    type     : 'sensor',
                    message  : 'Window intrusion detected!',
                    severity : 'danger',
                });
            }

            return {
                ...prev,
                timestamp       : new Date().toISOString(),
                source          : data.source      || prev.source,
                esp32_online    : data.esp32_online ?? prev.esp32_online,
                threat_level,
                hardware_outputs,
                sensors,
                ai_analysis: {
                    ...prev.ai_analysis,
                    face_detected,
                    verdict,
                    person_name,
                    confidence_score   : confidence,
                    bounding_box       : null,
                    latest_snapshot_url: null,
                },
                events: [...newEvents, ...prev.events].slice(0, 50),
            };
        });

        setConnectionStatus('connected');

    } catch (err) {
        console.error('[Sentinel] Poll error:', err);
        setConnectionStatus('error');
    }
}, []);

    useEffect(() => {
        poll(); // immediate first call
        intervalRef.current = setInterval(poll, 500);
        return () => clearInterval(intervalRef.current);
    }, [poll]);

    return (
        <SecurityContext.Provider value={{
            state,
            setState,
            connectionStatus,
            sendCommand,
            gasHistory,
            STREAM_URL,
        }}>
            {children}
        </SecurityContext.Provider>
    );
};

export const useSecurity = () => {
    const ctx = useContext(SecurityContext);
    if (!ctx) throw new Error('useSecurity must be used within SecurityProvider');
    return ctx;
};