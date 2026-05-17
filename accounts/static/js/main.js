(function() {
    const container = document.getElementById('authContainer');
    const switchToRegister = document.getElementById('switchToRegisterBtn');
    const switchToLogin = document.getElementById('switchToLoginBtn');
    const menuToggle = document.getElementById('menuToggle');
    const navMenu = document.getElementById('navMenu');
    const navbarLoginBtn = document.getElementById('navbarLoginBtn');
    const infoOverlay = document.getElementById('infoOverlay');
    const closeInfoBtn = document.getElementById('closeInfoBtn');
    const dynamicInfoContainer = document.getElementById('dynamicInfoContent');
    const navLinks = document.querySelectorAll('.nav-link');
    const homeLink = document.getElementById('homeLink');
    
    function showInfoPanel(type) {
        let htmlContent = '';
        
        if (type === 'about') {
            htmlContent = `
                <div class="modal-header">
                    <h2>✨ About LabHatud</h2>
                    <p>Revolutionizing the laundry industry with smart technology and sustainable practices</p>
                </div>
                <div class="modal-body">
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">10K+</div>
                            <div class="stat-label">Active Users</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">50+</div>
                            <div class="stat-label">Partner Laundries</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">100%</div>
                            <div class="stat-label">Satisfaction Rate</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">24/7</div>
                            <div class="stat-label">Customer Support</div>
                        </div>
                    </div>
                    
                    <div class="mission-section">
                        <h3 style="color:#1a6e53; margin-bottom:0.5rem;">🎯 Our Mission</h3>
                        <p>To revolutionize the laundry industry by offering fast, transparent, and eco-friendly services. We empower local businesses with smart tools and give customers a hassle-free laundry experience.</p>
                    </div>
                    
                    <h3 style="color:#1a6e53; margin:1rem 0 0.5rem 0;">💎 What We Offer</h3>
                    <div class="service-grid">
                        <div class="service-item"><div class="service-icon">🧼</div><strong>On-Demand Laundry</strong><span style="font-size:0.75rem;">Pickup & delivery in hours</span></div>
                        <div class="service-item"><div class="service-icon">🛵</div><strong>Rider Network</strong><span style="font-size:0.75rem;">Real-time tracking</span></div>
                        <div class="service-item"><div class="service-icon">🏪</div><strong>Owner Dashboard</strong><span style="font-size:0.75rem;">Manage orders & staff</span></div>
                        <div class="service-item"><div class="service-icon">⚡</div><strong>Smart Notifications</strong><span style="font-size:0.75rem;">Status updates via SMS/Email</span></div>
                        <div class="service-item"><div class="service-icon">♻️</div><strong>Eco-Friendly</strong><span style="font-size:0.75rem;">Biodegradable detergents</span></div>
                        <div class="service-item"><div class="service-icon">📊</div><strong>Analytics Hub</strong><span style="font-size:0.75rem;">Business insights</span></div>
                    </div>
                    
                    <h3 style="color:#1a6e53; margin:1rem 0 0.5rem 0;">🏆 Why Choose Us?</h3>
                    <div style="display:grid; grid-template-columns:repeat(2,1fr); gap:0.8rem; margin:1rem 0;">
                        <div style="display:flex; align-items:center; gap:8px;"><span style="color:#2bb3c0;">✓</span> Trusted by 10,000+ users</div>
                        <div style="display:flex; align-items:center; gap:8px;"><span style="color:#2bb3c0;">✓</span> 2-hour express service</div>
                        <div style="display:flex; align-items:center; gap:8px;"><span style="color:#2bb3c0;">✓</span> Secure payments</div>
                        <div style="display:flex; align-items:center; gap:8px;"><span style="color:#2bb3c0;">✓</span> 24/7 support</div>
                    </div>
                    
                    <div class="team-grid">
                        <div class="team-member">
                            <div class="team-avatar">👨‍💼</div>
                            <div class="team-name">John Anderson</div>
                            <div class="team-role">CEO & Founder</div>
                        </div>
                        <div class="team-member">
                            <div class="team-avatar">👩‍💻</div>
                            <div class="team-name">Sarah Chen</div>
                            <div class="team-role">CTO</div>
                        </div>
                        <div class="team-member">
                            <div class="team-avatar">👨‍🔧</div>
                            <div class="team-name">Mike Rodriguez</div>
                            <div class="team-role">Operations Head</div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            htmlContent = `
                <div class="modal-header">
                    <h2>📞 Contact Us</h2>
                    <p>We're here to help 24/7. Reach out through any channel below.</p>
                </div>
                <div class="modal-body">
                    <div class="contact-methods">
                        <div class="contact-row">
                            <div class="contact-icon">📧</div>
                            <div class="contact-info">
                                <strong>Email Support</strong>
                                <span>support@labhatud.com</span>
                                <span style="display:block; font-size:0.75rem;">careers@labhatud.com</span>
                            </div>
                        </div>
                        <div class="contact-row">
                            <div class="contact-icon">📞</div>
                            <div class="contact-info">
                                <strong>Phone / WhatsApp</strong>
                                <span>+1 (555) 123-4567</span>
                                <span style="display:block; font-size:0.75rem;">Mon-Fri: 8AM - 10PM EST</span>
                            </div>
                        </div>
                        <div class="contact-row">
                            <div class="contact-icon">💬</div>
                            <div class="contact-info">
                                <strong>Live Chat</strong>
                                <span>Available on mobile app & web portal</span>
                                <span style="display:block; font-size:0.75rem;">Response within 2 minutes</span>
                            </div>
                        </div>
                        <div class="contact-row">
                            <div class="contact-icon">📍</div>
                            <div class="contact-info">
                                <strong>Headquarters</strong>
                                <span>123 Innovation Drive, Suite 400</span>
                                <span style="display:block; font-size:0.75rem;">Austin, TX 78701</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="map-card">
                        <div class="map-icon">🗺️</div>
                        <strong>Global Presence</strong>
                        <p style="font-size:0.85rem; margin-top:0.5rem;">📍 Partner locations in 12+ cities across USA & expanding to Europe in 2025</p>
                    </div>
                    
                    <div class="social-links">
                        <a href="#" class="social-link">📘</a>
                        <a href="#" class="social-link">📸</a>
                        <a href="#" class="social-link">🐦</a>
                        <a href="#" class="social-link">🔗</a>
                        <a href="#" class="social-link">📺</a>
                    </div>
                    
                    <div style="margin-top:1.5rem; padding:1rem; background:#f0f9fa; border-radius:24px; text-align:center;">
                        <strong>📱 Download Our App</strong>
                        <div style="display:flex; gap:1rem; justify-content:center; margin-top:0.8rem;">
                            <span style="padding:6px 12px; background:#2bb3c0; color:white; border-radius:20px; font-size:0.75rem;">App Store</span>
                            <span style="padding:6px 12px; background:#2bb3c0; color:white; border-radius:20px; font-size:0.75rem;">Google Play</span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        dynamicInfoContainer.innerHTML = htmlContent;
        infoOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    function closeInfoPanel() {
        infoOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    function setActiveLink(activeId) {
        navLinks.forEach(link => {
            if (link.id === activeId) link.classList.add('active');
            else link.classList.remove('active');
        });
    }
    
    function setRegisterMode(active) {
        if (active) container.classList.add('register-active');
        else container.classList.remove('register-active');
    }
    
    function showLoginForm() {
        if (container.classList.contains('register-active')) setRegisterMode(false);
        const loginCard = document.getElementById('loginCard');
        if (loginCard) loginCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    document.getElementById('aboutNav')?.addEventListener('click', (e) => {
        e.preventDefault();
        setActiveLink('aboutNav');
        showInfoPanel('about');
    });
    
    document.getElementById('contactNav')?.addEventListener('click', (e) => {
        e.preventDefault();
        setActiveLink('contactNav');
        showInfoPanel('contact');
    });
    
    document.getElementById('homeNav')?.addEventListener('click', (e) => {
        e.preventDefault();
        setActiveLink('homeNav');
        if (infoOverlay.classList.contains('active')) closeInfoPanel();
        showLoginForm();
    });
    
    homeLink?.addEventListener('click', (e) => {
        e.preventDefault();
        setActiveLink('homeNav');
        if (infoOverlay.classList.contains('active')) closeInfoPanel();
        showLoginForm();
    });
    
    navbarLoginBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        if (infoOverlay.classList.contains('active')) closeInfoPanel();
        showLoginForm();
    });
    
    closeInfoBtn?.addEventListener('click', closeInfoPanel);
    infoOverlay?.addEventListener('click', (e) => { if (e.target === infoOverlay) closeInfoPanel(); });
    
    if (menuToggle && navMenu) {
        menuToggle.addEventListener('click', () => {
            menuToggle.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
        document.querySelectorAll('.nav-link, .nav-login-btn').forEach(link => {
            link.addEventListener('click', () => {
                menuToggle.classList.remove('active');
                navMenu.classList.remove('active');
            });
        });
    }
    
    switchToRegister?.addEventListener('click', (e) => {
        e.preventDefault();
        setRegisterMode(true);
        setTimeout(() => {
            const wrapper = document.querySelector('.register-scroll-wrapper');
            if (wrapper) wrapper.scrollTop = 0;
        }, 100);
    });
    
    switchToLogin?.addEventListener('click', (e) => { e.preventDefault(); showLoginForm(); });
    
    document.getElementById('loginFormElement')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = e.target.querySelector('input[name="username"]').value;
        alert(`✨ Welcome back, ${username}! Login successful.`);
    });
    
    document.getElementById('registerFormElement')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const password = document.getElementById('regPassword').value;
        const confirmPassword = document.getElementById('regConfirmPassword').value;
        if (password !== confirmPassword) { alert('❌ Passwords do not match!'); return; }
        if (password.length < 8) { alert('❌ Password must be at least 8 characters.'); return; }
        alert('🎉 Account created successfully! Please login to continue.');
        showLoginForm();
        e.target.reset();
    });
    
    setActiveLink('homeNav');
})();