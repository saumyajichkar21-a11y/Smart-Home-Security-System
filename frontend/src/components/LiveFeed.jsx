import React, { useRef, useEffect, useState, useCallback } from 'react';

const LiveFeed = ({ streamUrl, faceDetected, verdict, confidence, boundingBox }) => {
    const canvasRef  = useRef(null);
    const imgRef     = useRef(null);
    const [streamError, setStreamError] = useState(false);
    const [isLoading,   setIsLoading]   = useState(true);
    const [fps,         setFps]         = useState(0);
    const frameCount = useRef(0);
    const lastTime   = useRef(Date.now());
    const retryTimer = useRef(null);

    useEffect(() => {
        const interval = setInterval(() => {
            const now = Date.now();
            const elapsed = (now - lastTime.current) / 1000;
            setFps(Math.round(frameCount.current / elapsed));
            frameCount.current = 0;
            lastTime.current = now;
        }, 1000);
        return () => clearInterval(interval);
    }, []);

    const handleStreamError = useCallback(() => {
        setStreamError(true);
        setIsLoading(false);
        clearTimeout(retryTimer.current);
        retryTimer.current = setTimeout(() => {
            if (imgRef.current) {
                setStreamError(false);
                setIsLoading(true);
                imgRef.current.src = `${streamUrl}?t=${Date.now()}`;
            }
        }, 3000);
    }, [streamUrl]);

    const handleStreamLoad = useCallback(() => {
        setIsLoading(false);
        setStreamError(false);
        frameCount.current++;
    }, []);

    useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx    = canvas.getContext('2d');

    // Match canvas resolution to its display size
    const displayW = canvas.offsetWidth  || 640;
    const displayH = canvas.offsetHeight || 480;
    canvas.width   = displayW;
    canvas.height  = displayH;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!boundingBox) return;

    // Scale from 640x480 source to actual display size
    const scaleX = displayW / 640;
    const scaleY = displayH / 480;

    const [bx, by, bw, bh] = boundingBox;
    const x = bx * scaleX;
    const y = by * scaleY;
    const w = bw * scaleX;
    const h = bh * scaleY;

    const isUnknown = verdict === 'UNKNOWN' || verdict === 'UNKNOWN_ARMED';
    const boxColor  = isUnknown ? '#ff4757' : '#2ed573';

    ctx.shadowColor = boxColor;
    ctx.shadowBlur  = 14;
    ctx.strokeStyle = boxColor;
    ctx.lineWidth   = 2.5;
    ctx.strokeRect(x, y, w, h);
    ctx.shadowBlur  = 0;

    const label     = `${verdict}  ${((confidence || 0) * 100).toFixed(0)}%`;
    ctx.font        = 'bold 13px "JetBrains Mono", monospace';
    const tw        = ctx.measureText(label).width;
    ctx.fillStyle   = isUnknown ? 'rgba(255,71,87,0.85)' : 'rgba(46,213,115,0.85)';
    ctx.fillRect(x, y - 24, tw + 16, 24);
    ctx.fillStyle   = '#fff';
    ctx.fillText(label, x + 8, y - 7);
}, [boundingBox, verdict, confidence]);


    return (
        <div className="glass rounded-2xl overflow-hidden relative group">
            <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-sentinel-danger animate-pulse" />
                        <span className="text-sm font-semibold text-sentinel-200">LIVE FEED</span>
                    </div>
                    <span className="text-xs font-mono text-sentinel-400 bg-sentinel-800/50 px-2 py-1 rounded">CAM-01</span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-sentinel-400">{fps} FPS</span>
                    <span className="text-xs font-mono text-sentinel-gold">REC</span>
                </div>
            </div>

            <div className="relative aspect-video bg-sentinel-900">
                {isLoading && !streamError && (
                    <div className="absolute inset-0 flex items-center justify-center z-10">
                        <div className="shimmer w-full h-full absolute" />
                        <div className="relative z-10 text-center">
                            <div className="w-12 h-12 border-2 border-sentinel-gold/30 border-t-sentinel-gold rounded-full animate-spin mx-auto mb-3" />
                            <p className="text-sm text-sentinel-400">Connecting to stream...</p>
                        </div>
                    </div>
                )}

                {streamError && (
                    <div className="absolute inset-0 flex items-center justify-center z-10 bg-sentinel-900/80">
                        <div className="text-center">
                            <div className="text-3xl mb-2">📡</div>
                            <p className="text-sm text-sentinel-400">Stream offline — retrying...</p>
                        </div>
                    </div>
                )}

                <img
                    ref={imgRef}
                    src={streamUrl}
                    alt="Security Camera MJPEG Stream"
                    className="w-full h-full object-cover"
                    onLoad={handleStreamLoad}
                    onError={handleStreamError}
                />

                <canvas
                    ref={canvasRef}
                    width={640}
                    height={480}
                    className="absolute inset-0 w-full h-full pointer-events-none"
                />

                <div className="scan-line" />
                <div className="absolute top-4 left-4  w-8 h-8 border-l-2 border-t-2 border-sentinel-gold/50" />
                <div className="absolute top-4 right-4 w-8 h-8 border-r-2 border-t-2 border-sentinel-gold/50" />
                <div className="absolute bottom-4 left-4  w-8 h-8 border-l-2 border-b-2 border-sentinel-gold/50" />
                <div className="absolute bottom-4 right-4 w-8 h-8 border-r-2 border-b-2 border-sentinel-gold/50" />

                {faceDetected && (
                    <div className="absolute top-4 right-16 bg-sentinel-danger/80 backdrop-blur px-3 py-1 rounded-lg text-xs font-bold text-white animate-pulse">
                        FACE DETECTED
                    </div>
                )}

                <div className="absolute bottom-4 left-4 bg-black/50 backdrop-blur px-3 py-1 rounded text-xs font-mono text-sentinel-300">
                    {new Date().toISOString()}
                </div>
            </div>

            <div className="px-5 py-3 border-t border-white/5 bg-sentinel-800/30">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <svg className="w-4 h-4 text-sentinel-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                            </svg>
                            <span className="text-xs text-sentinel-400">AI Engine</span>
                        </div>
                        <div className={`px-2 py-1 rounded text-xs font-bold ${verdict === 'KNOWN' ? 'bg-sentinel-success/20 text-sentinel-success' : verdict === 'UNKNOWN' ? 'bg-sentinel-warning/20 text-sentinel-warning' : verdict === 'UNKNOWN_ARMED' ? 'bg-sentinel-danger/20 text-sentinel-danger animate-pulse' : 'bg-sentinel-700 text-sentinel-400'}`}>
                            {verdict || 'SCANNING'}
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-sentinel-400">Confidence</span>
                        <div className="w-24 h-2 rounded-full bg-sentinel-700 overflow-hidden">
                            <div className="h-full rounded-full bg-gradient-to-r from-sentinel-gold to-sentinel-goldLight transition-all duration-500" style={{ width: `${(confidence || 0) * 100}%` }} />
                        </div>
                        <span className="text-xs font-mono text-sentinel-gold w-10 text-right">
                            {confidence ? `${(confidence * 100).toFixed(0)}%` : '0%'}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LiveFeed;