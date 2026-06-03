import React from 'react';

const Timeline = ({ events }) => {
    const getSeverityColor = (severity) => {
        switch (severity) {
            case 'danger': return 'bg-sentinel-danger border-sentinel-danger';
            case 'warning': return 'bg-sentinel-warning border-sentinel-warning';
            case 'info': return 'bg-sentinel-info border-sentinel-info';
            default: return 'bg-sentinel-400 border-sentinel-400';
        }
    };

    const getSeverityText = (severity) => {
        switch (severity) {
            case 'danger': return 'text-sentinel-danger';
            case 'warning': return 'text-sentinel-warning';
            case 'info': return 'text-sentinel-info';
            default: return 'text-sentinel-400';
        }
    };

    const getTypeIcon = (type) => {
        switch (type) {
            case 'sensor':
                return (
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                );
            case 'ai':
                return (
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                );
            case 'status':
                return (
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                );
            default:
                return (
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                );
        }
    };

    return (
        <div className="glass rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
                <div className="flex items-center gap-3">
                    <svg className="w-5 h-5 text-sentinel-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="text-sm font-semibold text-sentinel-300">Event Timeline</h3>
                </div>
                <span className="text-xs text-sentinel-500 font-mono">
                    {events.length} events
                </span>
            </div>

            <div className="p-5 max-h-[500px] overflow-y-auto">
                {events.length === 0 ? (
                    <div className="text-center py-8">
                        <div className="w-12 h-12 rounded-full bg-sentinel-800/50 flex items-center justify-center mx-auto mb-3">
                            <svg className="w-6 h-6 text-sentinel-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <p className="text-sm text-sentinel-500">No events recorded yet</p>
                        <p className="text-xs text-sentinel-600 mt-1">Events will appear here when sensors trigger</p>
                    </div>
                ) : (
                    <div className="space-y-0">
                        {events.map((event, index) => (
                            <div 
                                key={event.id || index} 
                                className="timeline-item pb-4 animate-slide-up"
                                style={{ animationDelay: `${index * 50}ms` }}
                            >
                                <div className={`timeline-dot flex items-center justify-center ${getSeverityColor(event.severity)}`}>
                                    <div className="text-white">
                                        {getTypeIcon(event.type)}
                                    </div>
                                </div>
                                <div className="ml-2">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={`text-xs font-bold uppercase tracking-wider ${getSeverityText(event.severity)}`}>
                                            {event.severity}
                                        </span>
                                        <span className="text-[10px] text-sentinel-600">
                                            {new Date(event.timestamp).toLocaleTimeString('en-US', { hour12: false })}
                                        </span>
                                    </div>
                                    <p className="text-sm text-sentinel-300">{event.message}</p>
                                    <span className="text-[10px] text-sentinel-600 uppercase tracking-wider mt-1 block">
                                        {event.type}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Timeline;
