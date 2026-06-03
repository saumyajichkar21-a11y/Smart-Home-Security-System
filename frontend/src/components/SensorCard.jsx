import React from 'react';

const SensorCard = ({ title, value, unit, type, status, icon, history }) => {
    const getStatusColor = () => {
        switch (status) {
            case 'active':  return 'sentinel-success';
            case 'warning': return 'sentinel-warning';
            case 'danger':  return 'sentinel-danger';
            case 'normal':  return 'sentinel-400';
            default:        return 'sentinel-400';
        }
    };

    const getStatusText = () => {
        switch (status) {
            case 'active':  return 'TRIGGERED';
            case 'warning': return 'WARNING';
            case 'danger':  return 'ALERT';
            case 'normal':  return 'NORMAL';
            default:        return 'INACTIVE';
        }
    };

    const color = getStatusColor();

    return (
        <div className={`glass rounded-2xl p-5 transition-all duration-500 hover:bg-white/5 ${status === 'danger' ? 'threat-critical' : status === 'warning' ? 'threat-medium' : 'border-white/5'}`}>
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-xl bg-${color}/10 text-${color}`}>{icon}</div>
                    <div>
                        <h3 className="text-sm font-medium text-sentinel-300">{title}</h3>
                        <p className="text-[10px] text-sentinel-500 uppercase tracking-wider">{type}</p>
                    </div>
                </div>
                <div className={`status-dot ${status === 'active' || status === 'danger' ? 'active' : status === 'warning' ? 'warning' : ''}`} />
            </div>

            <div className="flex items-end justify-between">
                <div>
                    <span className={`text-2xl font-bold font-mono ${status === 'danger' ? 'text-sentinel-danger' : status === 'warning' ? 'text-sentinel-warning' : status === 'active' ? 'text-sentinel-success' : 'text-sentinel-200'}`}>
                        {value !== undefined ? value : '--'}
                    </span>
                    {unit && <span className="text-sm text-sentinel-500 ml-1">{unit}</span>}
                </div>
                <span className={`text-xs font-bold px-2 py-1 rounded-lg ${status === 'active' ? 'bg-sentinel-success/10 text-sentinel-success' : status === 'warning' ? 'bg-sentinel-warning/10 text-sentinel-warning' : status === 'danger' ? 'bg-sentinel-danger/10 text-sentinel-danger animate-pulse' : 'bg-sentinel-700/50 text-sentinel-500'}`}>
                    {getStatusText()}
                </span>
            </div>

            {history && history.length > 0 && (
                <div className="mt-3 h-8 flex items-end gap-[2px]">
                    {history.map((val, i) => {
                        const maxVal   = type === 'gas' ? 600 : 100;
                        const pct      = Math.max(4, Math.min(100, (val / maxVal) * 100));
                        const danger   = type === 'gas' ? val > 300 : val > 70;
                        const warn     = type === 'gas' ? val > 150 : val > 40;
                        const barColor = danger ? 'bg-sentinel-danger/70' : warn ? 'bg-sentinel-warning/60' : 'bg-sentinel-gold/30';
                        return <div key={i} className={`flex-1 rounded-sm transition-all duration-300 ${barColor}`} style={{ height: `${pct}%` }} />;
                    })}
                </div>
            )}
        </div>
    );
};

export default SensorCard;