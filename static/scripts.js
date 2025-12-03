// Initialize Icons
lucide.createIcons();

// --- 3D SCENE SETUP ---
const initThreeJS = () => {
    const container = document.getElementById('canvas-container');
    
    // Scene Setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050505, 0.002);
    scene.background = new THREE.Color(0x050505);

    // Camera
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 30;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // Particles (Starfield)
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 2000;
    const posArray = new Float32Array(particlesCount * 3);

    for(let i = 0; i < particlesCount * 3; i++) {
        posArray[i] = (Math.random() - 0.5) * 60;
    }

    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const particlesMaterial = new THREE.PointsMaterial({
        size: 0.15,
        color: 0x00ffff,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending
    });
    const particlesMesh = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particlesMesh);

    // Torus Knot (The spinning shape)
    const geometry2 = new THREE.TorusKnotGeometry(10, 3, 100, 16);
    const material2 = new THREE.PointsMaterial({
        color: 0xff00ff,
        size: 0.1,
        transparent: true,
        opacity: 0.5
    });
    const torusPoints = new THREE.Points(geometry2, material2);
    scene.add(torusPoints);

    // Mouse Interaction
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const windowHalfX = window.innerWidth / 2;
    const windowHalfY = window.innerHeight / 2;

    document.addEventListener('mousemove', (event) => {
        mouseX = (event.clientX - windowHalfX);
        mouseY = (event.clientY - windowHalfY);
    });

    // Animation Loop
    const animate = () => {
        requestAnimationFrame(animate);

        targetX = mouseX * 0.001;
        targetY = mouseY * 0.001;

        // Rotate based on time
        particlesMesh.rotation.y += 0.001;
        particlesMesh.rotation.x += 0.0005;
        torusPoints.rotation.y -= 0.002;
        torusPoints.rotation.x -= 0.001;

        // Rotate based on mouse
        particlesMesh.rotation.y += 0.05 * (targetX - particlesMesh.rotation.y);
        particlesMesh.rotation.x += 0.05 * (targetY - particlesMesh.rotation.x);

        renderer.render(scene, camera);
    };

    animate();

    // Handle Resize
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
};

// Run after page loads
window.addEventListener('load', initThreeJS);