// --- 1. 3D SCENE SETUP ---
const initThreeJS = () => {
    const container = document.getElementById('canvas-container');
    if(!container) return;

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050505, 0.002);
    
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 30;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // Particles
    const particlesGeometry = new THREE.BufferGeometry();
    const count = 2000;
    const posArray = new Float32Array(count * 3);
    for(let i=0; i<count*3; i++) posArray[i] = (Math.random()-0.5)*60;
    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const material = new THREE.PointsMaterial({size: 0.15, color: 0x00ffff, transparent:true, opacity:0.8});
    const mesh = new THREE.Points(particlesGeometry, material);
    scene.add(mesh);

    // Animation Loop
    const animate = () => {
        requestAnimationFrame(animate);
        mesh.rotation.y += 0.001;
        mesh.rotation.x += 0.0005;
        renderer.render(scene, camera);
    };
    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
};

// --- 2. HIGHLIGHTS & LIKES ---
async function loadPosts() {
    const container = document.getElementById('posts-container');
    if(!container) return;

    container.innerHTML = '<div class="text-gray-500 col-span-3 text-center">Loading highlights...</div>';

    try {
        const res = await fetch('/api/posts');
        const posts = await res.json();

        if(posts.length === 0) {
            container.innerHTML = '<div class="text-gray-500 col-span-3 text-center py-10">No highlights yet. Click "Admin" to add one!</div>';
            return;
        }

        container.innerHTML = posts.map(post => `
            <div class="bg-white/5 border border-white/10 rounded-2xl overflow-hidden hover:border-cyan-500/50 transition-all flex flex-col shadow-lg">
                <div class="h-48 bg-gray-800 relative">
                    ${post.image_url ? `<img src="${post.image_url}" class="w-full h-full object-cover">` : '<div class="flex items-center justify-center h-full text-gray-600">No Image</div>'}
                    <div class="absolute top-2 left-2 bg-black/60 px-2 py-1 text-xs text-cyan-300 font-bold rounded uppercase tracking-wider">${post.category}</div>
                </div>
                <div class="p-5 flex-1 flex flex-col">
                    <div class="text-xs text-cyan-400 font-bold mb-2 uppercase">${post.date}</div>
                    <h3 class="text-xl font-bold mb-2 leading-tight">${post.title}</h3>
                    <p class="text-gray-400 text-sm mb-4 flex-1 line-clamp-3">${post.description}</p>
                    <div class="border-t border-white/5 pt-3 flex items-center justify-between">
                        <button onclick="likePost(${post.id})" class="text-gray-400 hover:text-pink-500 text-xs flex items-center gap-1 transition-colors font-bold">
                            <i data-lucide="heart" size="14"></i> <span id="likes-${post.id}">${post.likes}</span> Likes
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        lucide.createIcons();
    } catch(e) {
        console.error(e);
        container.innerHTML = '<div class="text-red-500 text-center">Error loading posts.</div>';
    }
}

async function likePost(id) {
    await fetch(`/api/like/${id}`, {method: 'POST'});
    const likeCount = document.getElementById(`likes-${id}`);
    likeCount.innerText = parseInt(likeCount.innerText) + 1;
}

// --- 3. ADMIN ADD POST ---
async function adminPost() {
    const password = prompt("Enter Admin Password:");
    if(password !== "admin123") return alert("Wrong password!");

    const title = prompt("Post Title:");
    const description = prompt("Description:");
    const category = prompt("Category (Tech, Startup, Research):", "Tech");
    const image = prompt("Image URL (optional):");

    if(!title || !description) return;

    await fetch('/api/add_post', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'Admin-Key': password},
        body: JSON.stringify({title, description, category, image})
    });
    
    alert("Highlight added!");
    loadPosts();
}

// --- 4. AI CHAT ---
async function sendAIChat() {
    const input = document.getElementById('ai-input');
    const box = document.getElementById('chat-box');
    const msg = input.value.trim();
    if(!msg) return;

    // Add User Message
    box.innerHTML += `<div class="text-right mb-2"><span class="bg-cyan-600 text-white px-3 py-1.5 rounded-lg inline-block text-sm">${msg}</span></div>`;
    input.value = '';
    box.scrollTop = box.scrollHeight;

    // Add Loading
    const loadingId = 'loading-' + Date.now();
    box.innerHTML += `<div id="${loadingId}" class="text-left mb-2"><span class="bg-white/10 text-gray-300 px-3 py-1.5 rounded-lg inline-block text-xs">Thinking...</span></div>`;

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: msg})
        });
        const data = await res.json();
        
        document.getElementById(loadingId).remove();
        box.innerHTML += `<div class="text-left mb-2"><span class="bg-white/10 text-gray-200 px-3 py-1.5 rounded-lg inline-block text-sm">${data.response}</span></div>`;
        box.scrollTop = box.scrollHeight;
    } catch(e) {
        document.getElementById(loadingId).innerText = "Error connecting to AI.";
    }
}

// --- 5. CONTACT FORM ---
function toggleContactModal() {
    const modal = document.getElementById('contact-modal');
    modal.classList.toggle('hidden');
}

async function submitContact(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    const originalText = btn.innerText;
    
    const name = document.getElementById('c-name').value;
    const email = document.getElementById('c-email').value;
    const message = document.getElementById('c-msg').value;

    btn.innerText = "Sending...";
    btn.disabled = true;

    try {
        const res = await fetch('/api/contact', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name, email, message })
        });
        
        if (res.ok) {
            alert("Message saved successfully!");
            toggleContactModal();
            e.target.reset();
        } else {
            alert("Failed to send.");
        }
    } catch (error) {
        alert("Error sending message.");
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

// Initialize Everything
window.addEventListener('load', () => {
    initThreeJS();
    loadPosts();
    lucide.createIcons();
    
    // Toggle Chat
    document.getElementById('chat-toggle').addEventListener('click', () => {
        document.getElementById('chat-window').classList.remove('hidden');
    });
});