import React, { useState, useEffect } from 'react';
import LiveFeed from './components/LiveFeed.jsx';
import SensorCard from './components/SensorCard.jsx';
import HouseModel from './components/HouseModel.jsx';
import Timeline from './components/Timeline.jsx';
import ConnectionStatus from './components/ConnectionStatus.jsx';
import ThreatBanner from './components/ThreatBanner.jsx';
import { useSecurity } from './context/SecurityContext.jsx';

const App = () => {
    const { state, connectionStatus, sendCommand, gasHistory } = useSecurity();
    const [currentTime, setCurrentTime] = useState(new Date());
    const [sidebarOpen, setSidebarOpen] = useState(true);

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const formatTime = (date) => {
        return date.toLocaleTimeString('en-US', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
    };

    const formatDate = (date) => {
        return date.toLocaleDateString('en-US', { 
            weekday: 'short', 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    };

    return (
        <div className="min-h-screen bg-sentinel-900 text-sentinel-100">
            {/* Top Navigation Bar */}
            <nav className="fixed top-0 left-0 right-0 z-50 glass-strong border-b border-white/5">
                <div className="flex items-center justify-between px-6 py-3">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sentinel-gold to-sentinel-goldDark flex items-center justify-center">
                                <svg className="w-5 h-5 text-sentinel-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                </svg>
                            </div>
                            <div>
                                <h1 className="text-lg font-semibold tracking-tight text-sentinel-gold">SENTINEL</h1>
                                <p className="text-[10px] text-sentinel-400 tracking-widest uppercase">Intelligent Security Command</p>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => sendCommand(state.system_status === 'ARMED' ? 'disarm' : 'arm')}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold tracking-wider transition-all duration-300 ${
                                    state.system_status === 'ARMED'
                                        ? 'bg-sentinel-danger/20 text-sentinel-danger border border-sentinel-danger/30 hover:bg-sentinel-danger/30'
                                        : 'bg-sentinel-success/20 text-sentinel-success border border-sentinel-success/30 hover:bg-sentinel-success/30'
                                }`}
                            >
                                {state.system_status === 'ARMED' ? '🔴 DISARM' : '🟢 ARM'}
                            </button>
                            {(state.threat_level === 'HIGH' || state.threat_level === 'CRITICAL') && (
                                <button
                                    onClick={() => sendCommand('reset_alert')}
                                    className="px-3 py-1.5 rounded-lg text-xs font-bold tracking-wider bg-sentinel-warning/20 text-sentinel-warning border border-sentinel-warning/30 hover:bg-sentinel-warning/30 transition-all duration-300 animate-pulse"
                                >
                                    ⚠ RESET
                                </button>
                            )}
                        </div>
                        <ConnectionStatus status={connectionStatus} />

                        <div className="hidden md:flex items-center gap-2 text-sm font-mono text-sentinel-300">
                            <span className="text-sentinel-gold">{formatTime(currentTime)}</span>
                            <span className="text-sentinel-500">|</span>
                            <span className="text-sentinel-400">{formatDate(currentTime)}</span>
                        </div>

                        <button 
                            onClick={() => setSidebarOpen(!sidebarOpen)}
                            className="lg:hidden p-2 rounded-lg hover:bg-white/5 transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                            </svg>
                        </button>
                    </div>
                </div>
            </nav>

            {/* Threat Banner */}
            <ThreatBanner threatLevel={state.threat_level} systemStatus={state.system_status} />

            {/* Main Content */}
            <main className="pt-20 pb-6 px-4 md:px-6 max-w-[1600px] mx-auto">
                <div className="dashboard-grid grid grid-cols-1 lg:grid-cols-12 gap-5">

                    {/* Left Column - Live Feed & 3D Model */}
                    <div className="lg:col-span-8 space-y-5">
                        {/* Live Camera Feed */}
                        <LiveFeed 
                            streamUrl="http://10.85.83.237:81/stream"
                            faceDetected={state.ai_analysis?.face_detected}
                            verdict={state.ai_analysis?.verdict}
                            confidence={state.ai_analysis?.confidence_score}
                            boundingBox={state.ai_analysis?.bounding_box}
                        />

                        {/* 3D House Model */}
                        <HouseModel 
                            sensors={state.sensors}
                            hardwareOutputs={state.hardware_outputs}
                        />

                        {/* Sensor Grid */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                            <SensorCard 
                                title="PIR Motion"
                                value={state.sensors?.pir_motion}
                                unit=""
                                type="motion"
                                status={state.sensors?.pir_motion ? 'active' : 'inactive'}
                                icon={
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                    </svg>
                                }
                            />
                            <SensorCard 
                                title="Gas Sensor"
                                value={state.sensors?.mq2_gas_ppm}
                                unit="PPM"
                                type="gas"
                                status={state.sensors?.mq2_gas_ppm > 300 ? 'warning' : 'normal'}
                                history={gasHistory}
                                icon={
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                                    </svg>
                                }
                            />
                            <SensorCard 
                                title="Window Sensor"
                                value={state.sensors?.window_intrusion}
                                unit=""
                                type="contact"
                                status={state.sensors?.window_intrusion ? 'danger' : 'normal'}
                                icon={
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" />
                                    </svg>
                                }
                            />
                        </div>

                        {/* Hardware Outputs */}
                        <div className="glass rounded-2xl p-5">
                            <h3 className="text-sm font-semibold text-sentinel-300 mb-4 flex items-center gap-2">
                                <svg className="w-4 h-4 text-sentinel-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                Hardware Control
                            </h3>
                            <div className="grid grid-cols-3 gap-4">
                                <HardwareOutput 
                                    label="Relay"
                                    active={state.hardware_outputs?.relay_state}
                                    color="sentinel-gold"
                                />
                                <HardwareOutput 
                                    label="Siren"
                                    active={state.hardware_outputs?.buzzer_siren}
                                    color="sentinel-danger"
                                />
                                <HardwareOutput 
                                    label="Warning LED"
                                    active={state.hardware_outputs?.warning_led}
                                    color="sentinel-warning"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Right Column - Timeline & Status */}
                    <div className={`lg:col-span-4 space-y-5 ${sidebarOpen ? '' : 'hidden lg:block'}`}>
                        {/* System Status Card */}
                        <div className="glass rounded-2xl p-5">
                            <h3 className="text-sm font-semibold text-sentinel-300 mb-4">System Status</h3>
                            <div className="space-y-3">
                                <StatusRow label="Status" value={state.system_status} />
                                <StatusRow label="Threat Level" value={state.threat_level} />
                                <StatusRow label="Face Detected" value={state.ai_analysis?.face_detected ? 'YES' : 'NO'} />
                                <StatusRow label="Verdict" value={state.ai_analysis?.verdict || 'N/A'} />
                                <StatusRow 
                                    label="Confidence" 
                                    value={state.ai_analysis?.confidence_score ? `${(state.ai_analysis.confidence_score * 100).toFixed(1)}%` : 'N/A'} 
                                />
                            </div>
                        </div>

                        {/* AI Analysis Card */}
                        <div className="glass rounded-2xl p-5">
                            <h3 className="text-sm font-semibold text-sentinel-300 mb-4 flex items-center gap-2">
                                <svg className="w-4 h-4 text-sentinel-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                </svg>
                                AI Analysis
                            </h3>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between p-3 rounded-xl bg-sentinel-800/50">
                                    <span className="text-xs text-sentinel-400">Detection</span>
                                    <span className={`text-sm font-medium ${state.ai_analysis?.face_detected ? 'text-sentinel-success' : 'text-sentinel-400'}`}>
                                        {state.ai_analysis?.face_detected ? 'FACE DETECTED' : 'NO FACE'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between p-3 rounded-xl bg-sentinel-800/50">
                                    <span className="text-xs text-sentinel-400">Identity</span>
                                    <span className={`text-sm font-medium ${
                                        state.ai_analysis?.verdict === 'KNOWN' ? 'text-sentinel-success' :
                                        state.ai_analysis?.verdict === 'UNKNOWN' ? 'text-sentinel-warning' :
                                        'text-sentinel-400'
                                    }`}>
                                        {state.ai_analysis?.verdict || 'SCANNING...'}
                                    </span>
                                </div>
                                <div className="p-3 rounded-xl bg-sentinel-800/50">
                                    <div className="flex justify-between mb-2">
                                        <span className="text-xs text-sentinel-400">Confidence</span>
                                        <span className="text-xs font-mono text-sentinel-gold">
                                            {state.ai_analysis?.confidence_score ? `${(state.ai_analysis.confidence_score * 100).toFixed(1)}%` : '0%'}
                                        </span>
                                    </div>
                                    <div className="h-2 rounded-full bg-sentinel-700 overflow-hidden">
                                        <div 
                                            className="h-full rounded-full bg-gradient-to-r from-sentinel-gold to-sentinel-goldLight transition-all duration-500"
                                            style={{ width: `${(state.ai_analysis?.confidence_score || 0) * 100}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Event Timeline */}
                        <Timeline events={state.events || []} />
                    </div>
                </div>
            </main>
        </div>
    );
};

const StatusRow = ({ label, value }) => (
    <div className="flex items-center justify-between">
        <span className="text-xs text-sentinel-400">{label}</span>
        <span className="text-xs font-mono font-medium text-sentinel-200">{value}</span>
    </div>
);

const HardwareOutput = ({ label, active, color }) => (
    <div className={`p-3 rounded-xl border transition-all duration-300 ${
        active 
            ? `bg-${color}/10 border-${color}/30 shadow-lg shadow-${color}/10` 
            : 'bg-sentinel-800/30 border-white/5'
    }`}>
        <div className="flex items-center gap-2 mb-2">
            <div className={`w-2 h-2 rounded-full ${active ? `bg-${color} animate-pulse` : 'bg-sentinel-600'}`} />
            <span className={`text-xs font-medium ${active ? `text-${color}` : 'text-sentinel-500'}`}>
                {active ? 'ACTIVE' : 'OFF'}
            </span>
        </div>
        <span className="text-sm text-sentinel-300">{label}</span>
    </div>
);

export default App;
