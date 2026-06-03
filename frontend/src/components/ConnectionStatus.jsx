import React from 'react';

const ConnectionStatus = ({ status }) => {
    const getStatusConfig = () => {
        switch (status) {
            case 'connected':
                return {
                    dot: 'bg-sentinel-success',
                    pulse: 'animate-pulse',
                    text: 'Connected',
                    textColor: 'text-sentinel-success'
                };
            case 'connecting':
                return {
                    dot: 'bg-sentinel-warning',
                    pulse: 'animate-pulse',
                    text: 'Connecting...',
                    textColor: 'text-sentinel-warning'
                };
            case 'error':
                return {
                    dot: 'bg-sentinel-danger',
                    pulse: '',
                    text: 'Error',
                    textColor: 'text-sentinel-danger'
                };
            default:
                return {
                    dot: 'bg-sentinel-600',
                    pulse: '',
                    text: 'Offline',
                    textColor: 'text-sentinel-500'
                };
        }
    };

    const config = getStatusConfig();

    return (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-sentinel-800/50 border border-white/5">
            <div className={`w-2 h-2 rounded-full ${config.dot} ${config.pulse}`} />
            <span className={`text-xs font-medium ${config.textColor}`}>
                {config.text}
            </span>
        </div>
    );
};

export default ConnectionStatus;
