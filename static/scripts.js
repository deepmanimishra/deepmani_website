let isAdmin = false;
let adminKey = "";

// --- 1. 3D SCENE (FIXED MOUSE TRACKING) ---
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

    // Torus Knot
    const geo2 = new THREE.TorusKnotGeometry(10, 3, 100, 16);
    const mat2 = new THREE.PointsMaterial({color: 0xff00ff, size: 0.1, transparent: true, opacity: 0.5});
    const torus = new THREE.Points(geo2, mat2);
    scene.add(torus);

    // MOUSE TRACKING LOGIC
    let mouseX = 0, mouseY = 0;
    let targetX = 0, targetY = 0;
    const windowHalfX = window.innerWidth / 2;
    const windowHalfY = window.innerHeight / 2;

    document.addEventListener('mousemove', (event) => {
        mouseX = (event.clientX - windowHalfX);
        mouseY = (event.clientY - windowHalfY);
    });

    const animate = () => {
        requestAnimationFrame(animate);
        targetX = mouseX * 0.001;
        targetY = mouseY * 0.001;

        // Smooth rotation based on mouse
        mesh.rotation.y += 0.05 * (targetX - mesh.rotation.y);
        mesh.rotation.x += 0.05 * (targetY - mesh.rotation.x);
        torus.rotation.y += 0.05 * (targetX - torus.rotation.y);
        torus.rotation.x += 0.05 * (targetY - torus.rotation.x);

        // Auto rotation
        mesh.rotation.z += 0.001;

        renderer.render(scene, camera);
    };
    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
};

// --- 2. PROFILE & POSTS ---
async function loadProfile() {
    try {
        const res = await fetch('/api/profile');
        const data = await res.json();
        document.getElementById('hero-name').innerText = data.name;
        document.getElementById('nav-name').innerText = data.name + ".";
        document.getElementById('hero-bio').innerText = data.bio;
        document.getElementById('hero-sub-bio').innerText = data.sub_bio;
        document.getElementById('profile-img').src = data.image_url;
        
        // Populate Edit Modal Inputs
        document.getElementById('pf-name').value = data.name;
        document.getElementById('pf-bio').value = data.bio;
        document.getElementById('pf-sub').value = data.sub_bio;
        document.getElementById('pf-img').value = data.image_url;
    } catch(e) { console.error("Profile load error", e); }
}

async function loadPosts() {
    const container = document.getElementById('posts-container');
    container.innerHTML = '<div class="text-gray-500 col-span-3 text-center">Loading...</div>';
    try {
        const res = await fetch('/api/posts');
        const posts = await res.json();
        container.innerHTML = '';
        if(posts.length === 0) container.innerHTML = '<div class="text-gray-500 col-span-3 text-center">No highlights yet.</div>';

        posts.forEach(post => {
            const card = document.createElement('div');
            card.className = "bg-white/5 border border-white/10 rounded-2xl overflow-hidden hover:border-cyan-500/50 transition-all flex flex-col shadow-lg relative group";
            card.innerHTML = `
                <div class="h-48 bg-gray-800 relative">
                    ${post.image_url ? `<img src="${post.image_url}" class="w-full h-full object-cover">` : '<div class="flex items-center justify-center h-full text-gray-600">No Image</div>'}
                    <div class="absolute top-2 left-2 bg-black/60 px-2 py-1 text-xs text-cyan-300 font-bold rounded">${post.category}</div>
                    ${isAdmin ? `
                        <div class="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button onclick="editPost(${post.id}, '${post.title}', '${post.category}', '${post.image_url}', \`${post.description}\`)" class="p-2 bg-blue-600 rounded hover:bg-blue-500 text-white"><i data-lucide="pencil" size="14"></i></button>
                            <button onclick="deletePost(${post.id})" class="p-2 bg-red-600 rounded hover:bg-red-500 text-white"><i data-lucide="trash-2" size="14"></i></button>
                        </div>
                    ` : ''}
                </div>
                <div class="p-5 flex-1 flex flex-col">
                    <div class="text-xs text-cyan-400 font-bold mb-2">${post.date}</div>
                    <h3 class="text-xl font-bold mb-2">${post.title}</h3>
                    <p class="text-gray-400 text-sm mb-4 flex-1 line-clamp-3">${post.description}</p>
                    <div class="border-t border-white/5 pt-3 flex items-center justify-between">
                        <button onclick="likePost(${post.id})" class="text-gray-400 hover:text-pink-500 text-xs flex items-center gap-1 font-bold"><i data-lucide="heart" size="14"></i> <span id="likes-${post.id}">${post.likes}</span> Likes</button>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });
        lucide.createIcons();
    } catch(e) { container.innerHTML = "Error loading posts."; }
}

async function likePost(id) {
    await fetch(`/api/like/${id}`, {method: 'POST'});
    loadPosts();
}

// --- 3. ADMIN FUNCTIONS ---
function enableAdminMode() {
    const pw = prompt("Enter Admin Password:");
    if(pw === "admin123") {
        isAdmin = true;
        adminKey = pw;
        document.getElementById('add-post-btn').classList.remove('hidden');
        document.getElementById('edit-profile-btn').classList.remove('hidden');
        loadPosts(); // Reload to show buttons
        alert("Admin Mode Enabled!");
    } else {
        alert("Wrong Password");
    }
}

function toggleModal(id) { document.getElementById(id).classList.toggle('hidden'); }

// Profile
function openProfileModal() { toggleModal('profile-modal'); }
async function saveProfile() {
    const data = {
        name: document.getElementById('pf-name').value,
        bio: document.getElementById('pf-bio').value,
        sub_bio: document.getElementById('pf-sub').value,
        image: document.getElementById('pf-img').value
    };
    await fetch('/api/profile', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'Admin-Key': adminKey},
        body: JSON.stringify(data)
    });
    toggleModal('profile-modal');
    loadProfile();
}

// Posts
function openPostModal() {
    document.getElementById('post-modal-title').innerText = "Add Highlight";
    document.getElementById('post-id').value = "";
    document.getElementById('p-title').value = "";
    document.getElementById('p-desc').value = "";
    toggleModal('post-modal');
}

function editPost(id, title, cat, img, desc) {
    document.getElementById('post-modal-title').innerText = "Edit Highlight";
    document.getElementById('post-id').value = id;
    document.getElementById('p-title').value = title;
    document.getElementById('p-category').value = cat;
    document.getElementById('p-image').value = img;
    document.getElementById('p-desc').value = desc;
    toggleModal('post-modal');
}

async function savePost() {
    const id = document.getElementById('post-id').value;
    const data = {
        title: document.getElementById('p-title').value,
        description: document.getElementById('p-desc').value,
        category: document.getElementById('p-category').value,
        image: document.getElementById('p-image').value
    };
    
    const url = id ? `/api/posts/${id}` : '/api/posts';
    const method = id ? 'PUT' : 'POST';

    await fetch(url, {
        method: method,
        headers: {'Content-Type': 'application/json', 'Admin-Key': adminKey},
        body: JSON.stringify(data)
    });
    toggleModal('post-modal');
    loadPosts();
}

async function deletePost(id) {
    if(!confirm("Delete this highlight?")) return;
    await fetch(`/api/posts/${id}`, {
        method: 'DELETE',
        headers: {'Admin-Key': adminKey}
    });
    loadPosts();
}

// --- 4. SMART FEATURES (AI) ---
async function runSmartConnect() {
    const intent = document.getElementById('smart-intent').value;
    const resBox = document.getElementById('smart-result');
    if(!intent) return;
    
    resBox.classList.remove('hidden');
    resBox.innerText = "Drafting...";
    
    const res = await fetch('/api/smart_connect', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({intent})
    });
    const data = await res.json();
    resBox.innerText = data.response;
}

async function sendAIChat() {
    const input = document.getElementById('ai-input');
    const box = document.getElementById('chat-box');
    const msg = input.value;
    if(!msg) return;

    box.innerHTML += `<div class="text-right mb-2"><span class="bg-cyan-600 text-white px-3 py-1 rounded inline-block">${msg}</span></div>`;
    input.value = "";
    
    const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: msg})
    });
    const data = await res.json();
    box.innerHTML += `<div class="text-left mb-2"><span class="bg-white/10 text-gray-200 px-3 py-1 rounded inline-block">${data.response}</span></div>`;
    box.scrollTop = box.scrollHeight;
}

async function submitContact(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    btn.innerText = "Sending...";
    await fetch('/api/contact', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            name: document.getElementById('c-name').value,
            email: document.getElementById('c-email').value,
            message: document.getElementById('c-msg').value
        })
    });
    alert("Message Sent!");
    btn.innerText = "Send Message";
    toggleModal('contact-modal');
}

window.onload = () => {
    initThreeJS();
    loadProfile();
    loadPosts();
    lucide.createIcons();
    document.getElementById('chat-toggle').onclick = () => document.getElementById('chat-window').classList.remove('hidden');
};