import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

const HouseModel = ({ sensors, hardwareOutputs }) => {
    const containerRef = useRef(null);
    const rendererRef = useRef(null);
    const sceneRef = useRef(null);
    const cameraRef = useRef(null);
    const frameRef = useRef(null);

    useEffect(() => {
        if (!containerRef.current) return;

        // Scene setup
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0a0a0f);
        sceneRef.current = scene;

        // Camera
        const camera = new THREE.PerspectiveCamera(45, containerRef.current.clientWidth / 400, 0.1, 1000);
        camera.position.set(8, 6, 8);
        camera.lookAt(0, 0, 0);
        cameraRef.current = camera;

        // Renderer
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(containerRef.current.clientWidth, 400);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        containerRef.current.appendChild(renderer.domElement);
        rendererRef.current = renderer;

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(5, 10, 5);
        directionalLight.castShadow = true;
        scene.add(directionalLight);

        const pointLight = new THREE.PointLight(0xd4af37, 0.5, 20);
        pointLight.position.set(0, 5, 0);
        scene.add(pointLight);

        // Materials
        const wallMaterial = new THREE.MeshStandardMaterial({ 
            color: 0x1a1a25, 
            roughness: 0.8,
            metalness: 0.2
        });

        const windowMaterial = new THREE.MeshStandardMaterial({ 
            color: 0x3742fa, 
            roughness: 0.1, 
            metalness: 0.9,
            transparent: true,
            opacity: 0.7
        });

        const doorMaterial = new THREE.MeshStandardMaterial({ 
            color: 0x2d2d3a, 
            roughness: 0.9 
        });

        const roofMaterial = new THREE.MeshStandardMaterial({ 
            color: 0x252535, 
            roughness: 0.7 
        });

        // House group
        const houseGroup = new THREE.Group();

        // Main body
        const bodyGeometry = new THREE.BoxGeometry(4, 2.5, 3);
        const body = new THREE.Mesh(bodyGeometry, wallMaterial);
        body.position.y = 1.25;
        body.castShadow = true;
        body.receiveShadow = true;
        houseGroup.add(body);

        // Roof
        const roofGeometry = new THREE.ConeGeometry(3.5, 1.5, 4);
        const roof = new THREE.Mesh(roofGeometry, roofMaterial);
        roof.position.y = 3.25;
        roof.rotation.y = Math.PI / 4;
        roof.castShadow = true;
        houseGroup.add(roof);

        // Door
        const doorGeometry = new THREE.BoxGeometry(0.8, 1.8, 0.1);
        const door = new THREE.Mesh(doorGeometry, doorMaterial);
        door.position.set(0, 0.9, 1.55);
        houseGroup.add(door);

        // Windows
        const windowGeometry = new THREE.BoxGeometry(0.8, 0.8, 0.1);

        const window1 = new THREE.Mesh(windowGeometry, windowMaterial);
        window1.position.set(-1.2, 1.5, 1.55);
        houseGroup.add(window1);

        const window2 = new THREE.Mesh(windowGeometry, windowMaterial);
        window2.position.set(1.2, 1.5, 1.55);
        houseGroup.add(window2);

        // Sensor indicators
        const sensorGeometry = new THREE.SphereGeometry(0.15, 16, 16);

        // PIR Motion sensor (front door)
        const pirMaterial = new THREE.MeshStandardMaterial({ 
            color: sensors?.pir_motion ? 0xff4757 : 0x2ed573,
            emissive: sensors?.pir_motion ? 0xff4757 : 0x2ed573,
            emissiveIntensity: sensors?.pir_motion ? 0.8 : 0.2
        });
        const pirSensor = new THREE.Mesh(sensorGeometry, pirMaterial);
        pirSensor.position.set(0, 2.2, 1.6);
        houseGroup.add(pirSensor);

        // Window sensor
        const windowSensorMat = new THREE.MeshStandardMaterial({ 
            color: sensors?.window_intrusion ? 0xff4757 : 0x2ed573,
            emissive: sensors?.window_intrusion ? 0xff4757 : 0x2ed573,
            emissiveIntensity: sensors?.window_intrusion ? 0.8 : 0.2
        });
        const windowSensor = new THREE.Mesh(sensorGeometry, windowSensorMat);
        windowSensor.position.set(1.2, 1.5, 1.7);
        houseGroup.add(windowSensor);

        // Gas sensor (roof)
        const gasMaterial = new THREE.MeshStandardMaterial({ 
            color: sensors?.mq2_gas_ppm > 300 ? 0xffa502 : 0x2ed573,
            emissive: sensors?.mq2_gas_ppm > 300 ? 0xffa502 : 0x2ed573,
            emissiveIntensity: sensors?.mq2_gas_ppm > 300 ? 0.6 : 0.2
        });
        const gasSensor = new THREE.Mesh(sensorGeometry, gasMaterial);
        gasSensor.position.set(-1.5, 2.8, 0);
        houseGroup.add(gasSensor);

        // Warning LED on roof
        const ledGeometry = new THREE.SphereGeometry(0.1, 8, 8);
        const ledMaterial = new THREE.MeshStandardMaterial({ 
            color: hardwareOutputs?.warning_led ? 0xffa502 : 0x3a3a50,
            emissive: hardwareOutputs?.warning_led ? 0xffa502 : 0x000000,
            emissiveIntensity: hardwareOutputs?.warning_led ? 1 : 0
        });
        const led = new THREE.Mesh(ledGeometry, ledMaterial);
        led.position.set(0, 3.5, 0);
        houseGroup.add(led);

        scene.add(houseGroup);

        // Ground plane
        const groundGeometry = new THREE.PlaneGeometry(20, 20);
        const groundMaterial = new THREE.MeshStandardMaterial({ 
            color: 0x0a0a0f,
            roughness: 1,
            metalness: 0
        });
        const ground = new THREE.Mesh(groundGeometry, groundMaterial);
        ground.rotation.x = -Math.PI / 2;
        ground.receiveShadow = true;
        scene.add(ground);

        // Grid helper
        const gridHelper = new THREE.GridHelper(20, 20, 0x3a3a50, 0x1a1a25);
        scene.add(gridHelper);

        // Animation loop
        const animate = () => {
            frameRef.current = requestAnimationFrame(animate);

            // Rotate house slowly
            houseGroup.rotation.y += 0.002;

            // Pulse LED
            if (hardwareOutputs?.warning_led) {
                ledMaterial.emissiveIntensity = 0.5 + Math.sin(Date.now() * 0.005) * 0.5;
            }

            renderer.render(scene, camera);
        };
        animate();

        // Handle resize
        const handleResize = () => {
            if (!containerRef.current) return;
            const width = containerRef.current.clientWidth;
            const height = 400;
            camera.aspect = width / height;
            camera.updateProjectionMatrix();
            renderer.setSize(width, height);
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            cancelAnimationFrame(frameRef.current);
            renderer.dispose();
            if (containerRef.current && renderer.domElement) {
                containerRef.current.removeChild(renderer.domElement);
            }
        };
    }, []);

    // Update sensor colors when data changes
    useEffect(() => {
        if (!sceneRef.current) return;

        // Update materials based on sensor state
        sceneRef.current.traverse((child) => {
            if (child.isMesh && child.userData.sensorType) {
                // Update colors based on current state
            }
        });
    }, [sensors, hardwareOutputs]);

    return (
        <div className="glass rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
                <div className="flex items-center gap-3">
                    <svg className="w-5 h-5 text-sentinel-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                    </svg>
                    <h3 className="text-sm font-semibold text-sentinel-300">3D House Model</h3>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] text-sentinel-500 uppercase tracking-wider">Live</span>
                    <div className="w-2 h-2 rounded-full bg-sentinel-success animate-pulse" />
                </div>
            </div>
            <div 
                ref={containerRef} 
                id="house-model-container"
                className="w-full"
            />
            <div className="px-5 py-3 border-t border-white/5 flex items-center justify-between text-xs text-sentinel-500">
                <span>Sensor visualization</span>
                <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full bg-sentinel-success" /> Normal
                    </span>
                    <span className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full bg-sentinel-warning" /> Warning
                    </span>
                    <span className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full bg-sentinel-danger" /> Alert
                    </span>
                </div>
            </div>
        </div>
    );
};

export default HouseModel;
