let visitorIdentity = JSON.parse(localStorage.getItem('deepmani_visitor')) || null;
let currentPostId = null;

document.addEventListener('DOMContentLoaded', () => {
    initThreeJS();
    if(window.lucide) lucide.createIcons();
    updateIdentityUI();
});

// Create Toast Styles Dynamically so it works without touching CSS file
const style = document.createElement('style');
style.innerHTML = `
.toast { position: fixed; bottom: 20px; right: 20px; background: #000; border: 1px solid #06b6d4; color: #fff; padding: 12px 24px; border-radius: 8px; z-index: 100; opacity: 0; transition: opacity 0.3s; }
.toast.show { opacity: 1; }
.toast.error { border-color: #ef4444; }
.typing-dot { width: 6px; height: 6px; background: #fff; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out both; }
.typing-dot:nth-child(1) { animation-delay: -0.32s; }
.typing-dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }
`;
document.head.appendChild(style);

function showToast(msg, type='success') {
    let c = document.getElementById('toast-container');
    if(!c) {
        c = document.createElement('div');
        c.id = 'toast-container';
        document.body.appendChild(c);
    }
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = msg;
    c.appendChild(t);
    setTimeout(()=>t.classList.add('show'), 100);
    setTimeout(()=>{t.classList.remove('show'); setTimeout(()=>t.remove(), 300);}, 3000);
}

function initThreeJS() {
    const container = document.getElementById('three-container');
    if(!container) return; // Prevent crash if missing
    
    // Simple reset
    while(container.firstChild) container.removeChild(container.firstChild);

    const scene = new THREE.Scene(); 
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000); 
    camera.position.z = 30;
    
    const renderer = new THREE.WebGLRenderer({antialias:true, alpha:true}); 
    renderer.setSize(window.innerWidth, window.innerHeight); 
    container.appendChild(renderer.domElement);
    
    const geometry = new THREE.BufferGeometry();
    const count = 2000;
    const pos = new Float32Array(count * 3);
    for(let i=0; i<count*3; i++) pos[i] = (Math.random()-0.5)*60;
    geometry.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const material = new THREE.PointsMaterial({size:0.15, color:0x00ffff, transparent:true, opacity:0.8});
    const particles = new THREE.Points(geometry, material);
    scene.add(particles);
    
    const animate = () => {
        requestAnimationFrame(animate);
        particles.rotation.y += 0.001;
        particles.rotation.x += 0.0005;
        renderer.render(scene, camera);
    };
    animate();
    
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth/window.innerHeight; 
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}

// Global functions for HTML onClick
window.openModal = function(id) { 
    const el = document.getElementById(id);
    if(el) el.classList.remove('hidden'); 
}
window.closeModal = function(id) { 
    const el = document.getElementById(id);
    if(el) el.classList.add('hidden'); 
}
window.toggleMobileMenu = function() { document.getElementById('mobile-menu').classList.toggle('hidden'); }

window.submitAdminLogin = function() { 
    fetch('/api/admin/login', {
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body:JSON.stringify({password:document.getElementById('admin-password').value})
    })
    .then(r=>r.json())
    .then(d=>{ 
        if(d.status==='success') location.href='/dashboard'; 
        else showToast('Wrong Password','error'); 
    }); 
}

window.submitFollow = function(e) {
    e.preventDefault();
    fetch('/api/follow', {
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body:JSON.stringify({name:e.target.name.value, email:e.target.email.value})
    })
    .then(r=>r.json())
    .then(d=>{ 
        if(d.status==='error') showToast(d.message,'error'); 
        else { showToast(d.message); e.target.reset(); } 
    });
}

window.submitContact = function(e) {
    e.preventDefault(); 
    const btn=document.querySelector('#contactModal button[type="submit"]') || e.target.querySelector('button'); 
    const txt=btn ? btn.innerText : 'Send'; 
    if(btn) { btn.innerText='Sending...'; btn.disabled=true; }
    
    fetch('/api/contact', {
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body:JSON.stringify({name:e.target.name.value, email:e.target.email.value, message:e.target.message.value})
    }).then(() => {
        showToast('Message Sent!', 'success'); 
        window.closeModal('contactModal'); 
        e.target.reset(); 
        if(btn) { btn.innerText=txt; btn.disabled=false; }
    });
}

window.sendChatMessage = function() {
    const i=document.getElementById('chat-input'), t=i.value; 
    if(!t)return; 
    const m=document.getElementById('chat-messages'); 
    m.innerHTML+=`<div class="flex justify-end mb-2"><div class="bg-cyan-600 p-2 rounded text-sm text-white">${t}</div></div>`; 
    i.value='';
    
    const typing = document.createElement('div'); 
    typing.className = 'flex justify-start mb-2'; 
    typing.innerHTML = '<div class="bg-white/10 p-2 rounded text-sm flex gap-1"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>'; 
    m.appendChild(typing); 
    m.scrollTop=m.scrollHeight;
    
    fetch('/api/gemini', {
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body:JSON.stringify({prompt:t})
    })
    .then(r=>r.json())
    .then(d=>{ 
        m.removeChild(typing); 
        m.innerHTML+=`<div class="flex justify-start mb-2"><div class="bg-white/10 p-2 rounded text-sm text-gray-200">${d.response}</div></div>`; 
        m.scrollTop=m.scrollHeight; 
    });
}
window.toggleChat = function(){ document.getElementById('chat-window').classList.toggle('hidden'); }

// Identity Logic
window.setIdentity = function() { 
    const n=document.getElementById('visitor-name').value; 
    if(!n)return; 
    visitorIdentity={name:n, avatarInitial:n[0].toUpperCase()}; 
    localStorage.setItem('deepmani_visitor', JSON.stringify(visitorIdentity)); 
    window.closeModal('identityModal'); 
    updateIdentityUI(); 
}
window.updateIdentityUI = function() { 
    if(visitorIdentity){ 
        document.getElementById('guest-btn')?.classList.add('hidden'); 
        document.getElementById('auth-display')?.classList.remove('hidden'); 
        document.getElementById('auth-display')?.classList.add('flex'); 
        const av = document.getElementById('auth-avatar'); if(av) av.innerText=visitorIdentity.avatarInitial; 
        const nm = document.getElementById('auth-name'); if(nm) nm.innerText=visitorIdentity.name; 
    } else { 
        document.getElementById('guest-btn')?.classList.remove('hidden'); 
        document.getElementById('auth-display')?.classList.add('hidden'); 
    } 
}
window.clearIdentity = function() { localStorage.removeItem('deepmani_visitor'); location.reload(); }

// Post Interactions
window.openPostDetail = function(el) {
    currentPostId = el.dataset.id; 
    document.getElementById('detail-title').innerText=el.dataset.title; 
    document.getElementById('detail-desc').innerText=el.dataset.desc; 
    const i=document.getElementById('detail-image'); 
    if(el.dataset.image && el.dataset.image !== 'None'){i.src=el.dataset.image; i.style.display='block';} else i.style.display='none'; 
    document.getElementById('detail-likes').innerText=el.dataset.likes;
    
    fetch(`/api/posts/${currentPostId}/comments`).then(r=>r.json()).then(c=>{ 
        const l=document.getElementById('comments-list'); 
        l.innerHTML=''; 
        c.forEach(x=>{ l.innerHTML+=`<div class="flex gap-2 mb-2"><div class="font-bold text-cyan-400">${x.author_initial}:</div><div class="text-gray-300">${x.content}</div></div>`; }); 
    });
    window.openModal('postDetailModal');
}

window.likePost = function() { 
    if(!visitorIdentity) return window.openModal('identityModal'); 
    fetch(`/api/posts/${currentPostId}/like`, {method:'POST'}).then(r=>r.json()).then(d=>{ 
        document.getElementById('detail-likes').innerText=d.likes; 
    }); 
}

window.submitComment = function() { 
    if(!visitorIdentity) return window.openModal('identityModal'); 
    const t=document.getElementById('comment-input').value; 
    fetch(`/api/posts/${currentPostId}/comments`, {
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body:JSON.stringify({author:visitorIdentity.name, author_initial:visitorIdentity.avatarInitial, text:t})
    })
    .then(r=>r.json())
    .then(d=>{ 
        document.getElementById('comment-input').value=''; 
        // Refresh comments
        fetch(`/api/posts/${currentPostId}/comments`).then(r=>r.json()).then(c=>{ 
            const l=document.getElementById('comments-list'); 
            l.innerHTML=''; 
            c.forEach(x=>{ l.innerHTML+=`<div class="flex gap-2 mb-2"><div class="font-bold text-cyan-400">${x.author_initial}:</div><div class="text-gray-300">${x.content}</div></div>`; }); 
        });
    }); 
}

// Dashboard Functions
window.switchTab = function(t) { 
    document.querySelectorAll('.tab-content').forEach(e=>e.classList.add('hidden')); 
    const target = document.getElementById(`tab-${t}`);
    if(target) target.classList.remove('hidden'); 
}

// Only try to define these if elements exist (Dashboard specific)
window.submitPostWithCrop = function(e) { 
    e.preventDefault(); 
    // Fallback if no cropper
    let img = document.getElementById('post-image').value; 
    if(typeof cropper !== 'undefined' && cropper) img=cropper.getCroppedCanvas().toDataURL(); 
    
    fetch('/api/posts', {
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body:JSON.stringify({
            title:document.getElementById('post-title').value, 
            category:document.getElementById('post-category').value, 
            description:document.getElementById('post-desc').value, 
            imageUrl:img
        })
    }).then(()=>location.reload()); 
}