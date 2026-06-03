import React, { useEffect, useState } from 'react';

const ThreatBanner = ({ threatLevel, systemStatus }) => {
    const [visible, setVisible] = useState(false);
    const [audioPlayed, setAudioPlayed] = useState(false);

    useEffect(() => {
        if (threatLevel === 'HIGH' || threatLevel === 'CRITICAL') {
            setVisible(true);
            if (!audioPlayed) {
                // Play warning chime
                playWarningChime();
                setAudioPlayed(true);
            }
        } else {
            setVisible(false);
            setAudioPlayed(false);
        }
    }, [threatLevel, audioPlayed]);

    const playWarningChime = () => {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.setValueAtTime(440, audioContext.currentTime);
            oscillator.frequency.exponentialRampToValueAtTime(880, audioContext.currentTime + 0.1);

            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (e) {
            console.log('Audio not supported');
        }
    };

    if (!visible) return null;

    const getBannerConfig = () => {
        switch (threatLevel) {
            case 'CRITICAL':
                return {
                    bg: 'bg-sentinel-danger/20 border-sentinel-danger/50',
                    text: 'text-sentinel-danger',
                    icon: (
                        <svg className="w-5 h-5 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                    ),
                    message: 'CRITICAL THREAT DETECTED — UNKNOWN ARMED INTRUDER'
                };
            case 'HIGH':
                return {
                    bg: 'bg-sentinel-warning/20 border-sentinel-warning/50',
                    text: 'text-sentinel-warning',
                    icon: (
                        <svg className="w-5 h-5 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    ),
                    message: 'HIGH THREAT LEVEL — UNKNOWN PERSON DETECTED'
                };
            default:
                return {
                    bg: 'bg-sentinel-info/20 border-sentinel-info/50',
                    text: 'text-sentinel-info',
                    icon: null,
                    message: ''
                };
        }
    };

    const config = getBannerConfig();

    return (
        <div className={`fixed top-14 left-0 right-0 z-40 ${config.bg} border-b backdrop-blur-md transition-all duration-500`}>
            <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    {config.icon}
                    <span className={`text-sm font-bold tracking-wider ${config.text}`}>
                        {config.message}
                    </span>
                </div>
                <div className="flex items-center gap-4">
                    <span className="text-xs text-sentinel-400">
                        System: <span className={systemStatus === 'ARMED' ? 'text-sentinel-danger font-bold' : 'text-sentinel-success'}>{systemStatus}</span>
                    </span>
                    <button 
                        onClick={() => setVisible(false)}
                        className="text-xs text-sentinel-500 hover:text-sentinel-300 transition-colors"
                    >
                        Dismiss
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ThreatBanner;
