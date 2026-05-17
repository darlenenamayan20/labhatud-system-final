(function() {
    const loadingScreen = document.getElementById('loadingScreen');
    const progressFill = document.getElementById('progressFill');
    const percentageSpan = document.getElementById('progressPercent');
    const statusSpan = document.getElementById('loadingStatus');
    
    const statusMessages = [
        'Initializing secure connection...',
        'Loading premium features...',
        'Preparing your dashboard...',
        'Almost ready...',
        'Welcome to LabHatud!'
    ];
    
    let progress = 0;
    let messageIndex = 0;
    
    function updateProgress() {
        if (progress < 100) {
            progress += Math.random() * 12 + 4;
            if (progress > 100) progress = 100;
            
            if (progressFill) progressFill.style.width = progress + '%';
            if (percentageSpan) percentageSpan.textContent = Math.floor(progress) + '%';
            
            if (progress >= 20 && messageIndex === 0) {
                messageIndex = 1;
                if (statusSpan) statusSpan.textContent = statusMessages[1];
            } else if (progress >= 45 && messageIndex === 1) {
                messageIndex = 2;
                if (statusSpan) statusSpan.textContent = statusMessages[2];
            } else if (progress >= 70 && messageIndex === 2) {
                messageIndex = 3;
                if (statusSpan) statusSpan.textContent = statusMessages[3];
            } else if (progress >= 90 && messageIndex === 3) {
                messageIndex = 4;
                if (statusSpan) statusSpan.textContent = statusMessages[4];
            }
            
            if (progress < 100) {
                setTimeout(updateProgress, 180 + Math.random() * 120);
            } else {
                setTimeout(() => {
                    if (loadingScreen) {
                        loadingScreen.classList.add('fade-out');
                        setTimeout(() => {
                            loadingScreen.style.display = 'none';
                            const navbar = document.getElementById('navbar');
                            const authContainer = document.getElementById('authContainer');
                            if (navbar) navbar.classList.add('visible');
                            if (authContainer) authContainer.classList.add('visible');
                        }, 800);
                    }
                }, 400);
            }
        }
    }
    
    setTimeout(updateProgress, 300);
})();