let visitorIdentity = JSON.parse(localStorage.getItem('deepmani_visitor')) || null;
let currentPostId = null;

// FORCE START
document.addEventListener('DOMContentLoaded', () => {
    initThreeJS();
    lucide.createIcons();
    updateIdentityUI();
});

function showToast(msg, type='success') {
    const c = document.getElementById('toast-container'); const t = document.createElement('div');
    t.className = `toast ${type}`; t.innerHTML = type==='success' ? `<i data-lucide="check"></i> ${msg}` : `<i data-lucide="alert-circle"></i> ${msg}`;
    c.appendChild(t); lucide.createIcons();
    setTimeout(()=>t.classList.add('show'), 100); setTimeout(()=>{t.classList.remove('show'); setTimeout(()=>t.remove(), 300);}, 3000);
}

// --- 3D SCENE (CONSTANT ROTATION FIX) ---
function initThreeJS() {
    const container = document.getElementById('three-container');
    if(!container) return;
    
    // Cleanup previous if exists
    while(container.firstChild) container.removeChild(container.firstChild);

    const scene = new THREE.Scene(); 
    scene.fog = new THREE.FogExp2(0x050505, 0.002);
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000); 
    camera.position.z = 30;
    
    const renderer = new THREE.WebGLRenderer({antialias:true, alpha:true}); 
    renderer.setSize(window.innerWidth, window.innerHeight); 
    container.appendChild(renderer.domElement);
    
    // Particles
    const geometry = new THREE.BufferGeometry();
    const count = 2000;
    const pos = new Float32Array(count * 3);
    for(let i=0; i<count*3; i++) pos[i] = (Math.random()-0.5)*60;
    geometry.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const material = new THREE.PointsMaterial({size:0.15, color:0x00ffff, transparent:true, opacity:0.8});
    const particles = new THREE.Points(geometry, material);
    scene.add(particles);
    
    // Torus
    const torusGeo = new THREE.TorusKnotGeometry(10,3,100,16);
    const torusMat = new THREE.PointsMaterial({color:0xff00ff, size:0.1, transparent:true, opacity:0.5});
    const torus = new THREE.Points(torusGeo, torusMat);
    scene.add(torus);
    
    let mouseX = 0, mouseY = 0;
    document.addEventListener('mousemove', (e) => {
        mouseX = (e.clientX - window.innerWidth/2) * 0.001;
        mouseY = (e.clientY - window.innerHeight/2) * 0.001;
    });

    // INFINITE LOOP
    const animate = () => {
        requestAnimationFrame(animate);
        
        // Constant rotation regardless of mouse
        particles.rotation.y += 0.001;
        particles.rotation.x += 0.0005;
        torus.rotation.y -= 0.002;
        torus.rotation.x -= 0.001;
        
        // Add subtle mouse influence
        particles.rotation.y += 0.05 * (mouseX - particles.rotation.y);
        particles.rotation.x += 0.05 * (mouseY - particles.rotation.x);
        
        renderer.render(scene, camera);
    };
    animate();
    
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth/window.innerHeight; 
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}

function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }
function toggleMobileMenu() { document.getElementById('mobile-menu').classList.toggle('hidden'); }
function switchTab(t) { 
    document.querySelectorAll('.tab-content').forEach(e=>e.classList.add('hidden')); 
    document.getElementById(`tab-${t}`).classList.remove('hidden'); 
    document.querySelectorAll('.tab-btn').forEach(b => { b.classList.remove('bg-cyan-600'); b.classList.add('bg-white/10'); });
    event.target.classList.remove('bg-white/10'); event.target.classList.add('bg-cyan-600');
}
function openDocModal(path) { document.getElementById('doc-iframe').src = path; openModal('docModal'); }

function submitFollow(e) {
    e.preventDefault();
    fetch('/api/follow', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:e.target.name.value, email:e.target.email.value})})
    .then(r=>r.json()).then(d=>{ if(d.status==='error') showToast(d.message,'error'); else { showToast(d.message); e.target.reset(); } });
}

function submitContact(e) {
    e.preventDefault(); const btn=document.getElementById('contact-submit-btn'); const txt=btn.innerHTML; btn.innerHTML='<span class="loader"></span>'; btn.disabled=true;
    // Fast send feedback
    setTimeout(() => { showToast('Message Sent!', 'success'); closeModal('contactModal'); e.target.reset(); btn.innerHTML=txt; btn.disabled=false; }, 500);
    fetch('/api/contact', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:e.target.name.value, email:e.target.email.value, message:e.target.message.value})});
}

function submitAdminLogin() { fetch('/api/admin/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({password:document.getElementById('admin-password').value})}).then(r=>r.json()).then(d=>{ if(d.status==='success') location.href='/dashboard'; else showToast('Wrong Password','error'); }); }
function submitPostWithCrop(e) { e.preventDefault(); let img=''; if(cropper) img=cropper.getCroppedCanvas().toDataURL(); fetch('/api/posts', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title:document.getElementById('post-title').value, category:document.getElementById('post-category').value, description:document.getElementById('post-desc').value, imageUrl:img})}).then(()=>location.reload()); }
function deletePost(id) { if(confirm('Delete?')) fetch(`/api/posts/${id}`, {method:'DELETE'}).then(()=>location.reload()); }
function addJourney(e) { e.preventDefault(); fetch('/api/journey', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({year:document.getElementById('j-year').value, title:document.getElementById('j-title').value, description:document.getElementById('j-desc').value})}).then(()=>location.reload()); }
function deleteJourney(id) { if(confirm('Delete?')) fetch(`/api/journey/${id}`, {method:'DELETE'}).then(()=>location.reload()); }
function uploadDocument(e) { e.preventDefault(); const fd=new FormData(); fd.append('title', document.getElementById('doc-title').value); fd.append('file', document.getElementById('doc-file').files[0]); fetch('/api/documents', {method:'POST', body:fd}).then(()=>location.reload()); }
function deleteDocument(id) { if(confirm('Delete?')) fetch(`/api/documents/${id}`, {method:'DELETE'}).then(()=>location.reload()); }

function setIdentity() { const n=document.getElementById('visitor-name').value; if(!n)return; visitorIdentity={name:n, avatarInitial:n[0].toUpperCase()}; localStorage.setItem('deepmani_visitor', JSON.stringify(visitorIdentity)); closeModal('identityModal'); updateIdentityUI(); if(document.getElementById('contact-name')) document.getElementById('contact-name').value=n; }
function updateIdentityUI() { if(visitorIdentity){ document.getElementById('guest-btn')?.classList.add('hidden'); document.getElementById('auth-display')?.classList.remove('hidden'); document.getElementById('auth-display')?.classList.add('flex'); document.getElementById('auth-avatar').innerText=visitorIdentity.avatarInitial; document.getElementById('auth-name').innerText=visitorIdentity.name; } else { document.getElementById('guest-btn')?.classList.remove('hidden'); document.getElementById('auth-display')?.classList.add('hidden'); } }
function clearIdentity() { localStorage.removeItem('deepmani_visitor'); location.reload(); }

function sendChatMessage() {
    const i=document.getElementById('chat-input'), t=i.value; if(!t)return; const m=document.getElementById('chat-messages'); m.innerHTML+=`<div class="flex justify-end mb-2"><div class="bg-cyan-600 p-2 rounded text-sm text-white">${t}</div></div>`; i.value='';
    const typing = document.createElement('div'); typing.className = 'flex justify-start mb-2'; typing.innerHTML = '<div class="bg-white/10 p-2 rounded text-sm flex gap-1"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>'; m.appendChild(typing); m.scrollTop=m.scrollHeight;
    
    // Explicitly pass guest name here
    const user = visitorIdentity ? visitorIdentity.name : 'Guest';
    fetch('/api/gemini', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({prompt:t, user: user})}).then(r=>r.json()).then(d=>{ m.removeChild(typing); m.innerHTML+=`<div class="flex justify-start mb-2"><div class="bg-white/10 p-2 rounded text-sm text-gray-200">${d.response}</div></div>`; m.scrollTop=m.scrollHeight; });
}
function toggleChat(){ document.getElementById('chat-window').classList.toggle('hidden'); }

// UPDATED: "Drafting..." Animation
function generateConnectMessage() { 
    const i=document.getElementById('ai-connect-intent').value; if(!i)return; 
    const btn = document.getElementById('ai-connect-btn');
    const oldText = btn.innerText;
    btn.innerHTML = `<span class="loader"></span> Drafting...`;
    btn.disabled = true;
    
    fetch('/api/gemini', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({prompt:`Draft a note: ${i}`})})
    .then(r=>r.json()).then(d=>{ 
        document.getElementById('ai-connect-result').classList.remove('hidden'); 
        document.getElementById('ai-connect-text').innerText=d.response; 
        btn.innerHTML = oldText;
        btn.disabled = false;
    }); 
}
function copyToClipboard() { navigator.clipboard.writeText(document.getElementById('ai-connect-text').innerText); showToast('Copied!'); }

function openPostDetail(el) {
    currentPostId = el.dataset.id; document.getElementById('detail-title').innerText=el.dataset.title; document.getElementById('detail-desc').innerText=el.dataset.desc; const i=document.getElementById('detail-image'); if(el.dataset.image){i.src=el.dataset.image; i.style.display='block';}else i.style.display='none'; document.getElementById('detail-likes').innerText=el.dataset.likes;
    fetch(`/api/posts/${currentPostId}/comments`).then(r=>r.json()).then(c=>{ const l=document.getElementById('comments-list'); l.innerHTML=''; c.forEach(x=>{ l.innerHTML+=`<div class="flex gap-2 mb-2"><div class="font-bold text-cyan-400">${x.author_initial}:</div><div class="text-gray-300">${x.content}</div></div>`; }); });
    openModal('postDetailModal');
}
function likePost() { if(!visitorIdentity)return openModal('identityModal'); fetch(`/api/posts/${currentPostId}/like`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({user:visitorIdentity.name})}).then(r=>r.json()).then(d=>{ if(d.error) showToast('Blocked by Admin','error'); else document.getElementById('detail-likes').innerText=d.likes; }); }
function submitComment() { if(!visitorIdentity)return openModal('identityModal'); const t=document.getElementById('comment-input').value; fetch(`/api/posts/${currentPostId}/comments`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({author:visitorIdentity.name, author_initial:visitorIdentity.avatarInitial, text:t})}).then(r=>r.json()).then(d=>{ if(d.error) showToast('Blocked by Admin','error'); else { document.getElementById('comment-input').value=''; openPostDetail({dataset:{id:currentPostId, title:document.getElementById('detail-title').innerText, desc:document.getElementById('detail-desc').innerText, image:document.getElementById('detail-image').src, likes:document.getElementById('detail-likes').innerText}}); } }); }