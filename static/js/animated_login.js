// Animated Login JavaScript - Enhanced Interactions

class AnimatedLogin {
    constructor() {
        this.isAnimationComplete = false;
        this.particles = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startAnimation();
        this.setupFormValidation();
        this.createParticles();
    }

    setupEventListeners() {
        // Form submission with loading animation
        const form = document.querySelector('form');
        const submitBtn = document.querySelector('.btn-login');
        
        if (form && submitBtn) {
            form.addEventListener('submit', (e) => {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
                
                // Re-enable after 5 seconds if no redirect
                setTimeout(() => {
                    submitBtn.classList.remove('loading');
                    submitBtn.disabled = false;
                }, 5000);
            });
        }

        // Enhanced input interactions
        const inputs = document.querySelectorAll('.form-control');
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                input.parentElement.classList.add('focused');
                this.animateLabel(input);
            });

            input.addEventListener('blur', () => {
                if (!input.value) {
                    input.parentElement.classList.remove('focused');
                }
            });

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    const nextInput = this.getNextInput(input);
                    if (nextInput) {
                        nextInput.focus();
                    } else {
                        form.submit();
                    }
                }
            });
        });

        // Character interaction
        const character = document.querySelector('.character');
        if (character) {
            character.addEventListener('click', () => {
                this.animateCharacterGreeting();
            });
        }
    }

    startAnimation() {
        const character = document.querySelector('.character');
        const briefcase = document.querySelector('.briefcase');
        const form = document.querySelector('.login-form');

        if (!character || !briefcase || !form) return;

        // Character walking animation
        setTimeout(() => {
            character.classList.add('character-walking');
        }, 500);

        // Briefcase drop animation
        setTimeout(() => {
            briefcase.classList.add('briefcase-drop');
            this.createParticleExplosion();
        }, 3200);

        // Form emergence animation
        setTimeout(() => {
            form.classList.add('form-emerge');
            this.animateFormElements();
            this.isAnimationComplete = true;
        }, 3800);
    }

    animateFormElements() {
        const formGroups = document.querySelectorAll('.form-group');
        formGroups.forEach((group, index) => {
            setTimeout(() => {
                group.style.animation = `slideInForm 0.6s ease-out forwards`;
            }, index * 200);
        });
    }

    animateLabel(input) {
        const label = input.parentElement.querySelector('.form-label');
        if (label) {
            label.style.animation = 'labelFloat 0.3s ease-out forwards';
        }
    }

    animateCharacterGreeting() {
        const character = document.querySelector('.character');
        const smile = document.querySelector('.character-smile');
        const eyes = document.querySelectorAll('.eye');
        
        if (character && this.isAnimationComplete) {
            // Enhanced greeting animation
            character.style.animation = 'bounce 0.6s ease-in-out';
            
            // Make smile bigger
            if (smile) {
                smile.style.animation = 'bigSmile 0.8s ease-in-out';
            }
            
            // Make eyes blink faster
            eyes.forEach(eye => {
                eye.style.animation = 'fastBlink 0.3s ease-in-out 3';
            });
            
            // Wave arms
            const arms = document.querySelectorAll('.arm');
            arms.forEach(arm => {
                arm.style.animation = 'wave 0.5s ease-in-out 2';
            });
            
            setTimeout(() => {
                character.style.animation = 'none';
                if (smile) smile.style.animation = 'smile 2s infinite ease-in-out';
                eyes.forEach(eye => {
                    eye.style.animation = 'blink 4s infinite';
                });
                arms.forEach(arm => {
                    arm.style.animation = 'armSwing 0.8s infinite ease-in-out';
                });
            }, 800);
        }
    }

    createParticles() {
        const container = document.querySelector('.animation-scene');
        if (!container) return;

        for (let i = 0; i < 20; i++) {
            setTimeout(() => {
                this.createFloatingParticle(container);
            }, Math.random() * 2000);
        }
    }

    createFloatingParticle(container) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * window.innerWidth + 'px';
        particle.style.top = window.innerHeight + 'px';
        
        container.appendChild(particle);

        setTimeout(() => {
            particle.remove();
        }, 3000);
    }

    createParticleExplosion() {
        const briefcase = document.querySelector('.briefcase');
        if (!briefcase) return;

        const rect = briefcase.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        for (let i = 0; i < 15; i++) {
            setTimeout(() => {
                this.createExplosionParticle(centerX, centerY);
            }, i * 50);
        }
    }

    createExplosionParticle(x, y) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.position = 'fixed';
        particle.style.left = x + 'px';
        particle.style.top = y + 'px';
        particle.style.zIndex = '10';

        const angle = Math.random() * Math.PI * 2;
        const velocity = Math.random() * 100 + 50;
        const deltaX = Math.cos(angle) * velocity;
        const deltaY = Math.sin(angle) * velocity;

        document.body.appendChild(particle);

        let currentX = x;
        let currentY = y;
        let opacity = 1;

        const animate = () => {
            currentX += deltaX * 0.02;
            currentY += deltaY * 0.02;
            opacity -= 0.02;

            particle.style.left = currentX + 'px';
            particle.style.top = currentY + 'px';
            particle.style.opacity = opacity;

            if (opacity > 0) {
                requestAnimationFrame(animate);
            } else {
                particle.remove();
            }
        };

        requestAnimationFrame(animate);
    }

    setupFormValidation() {
        const form = document.querySelector('form');
        if (!form) return;

        form.addEventListener('submit', (e) => {
            const isValid = this.validateForm();
            if (!isValid) {
                e.preventDefault();
                this.showValidationErrors();
            }
        });
    }

    validateForm() {
        const username = document.querySelector('#id_username');
        const password = document.querySelector('#id_password');
        let isValid = true;

        this.clearValidationErrors();

        if (!username || !username.value.trim()) {
            this.showFieldError(username, 'اسم المستخدم مطلوب');
            isValid = false;
        }

        if (!password || !password.value.trim()) {
            this.showFieldError(password, 'كلمة المرور مطلوبة');
            isValid = false;
        }

        return isValid;
    }

    showFieldError(field, message) {
        if (!field) return;

        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        errorDiv.style.color = '#dc3545';
        errorDiv.style.fontSize = '0.875rem';
        errorDiv.style.marginTop = '0.25rem';

        field.style.borderColor = '#dc3545';
        field.parentElement.appendChild(errorDiv);

        // Shake animation
        field.style.animation = 'shake 0.5s ease-in-out';
        setTimeout(() => {
            field.style.animation = 'none';
        }, 500);
    }

    showValidationErrors() {
        const form = document.querySelector('.login-form');
        if (form) {
            form.style.animation = 'shake 0.5s ease-in-out';
            setTimeout(() => {
                form.style.animation = 'none';
            }, 500);
        }
    }

    clearValidationErrors() {
        const errors = document.querySelectorAll('.field-error');
        errors.forEach(error => error.remove());

        const inputs = document.querySelectorAll('.form-control');
        inputs.forEach(input => {
            input.style.borderColor = '#e1e5e9';
        });
    }

    getNextInput(currentInput) {
        const inputs = Array.from(document.querySelectorAll('.form-control'));
        const currentIndex = inputs.indexOf(currentInput);
        return inputs[currentIndex + 1] || null;
    }
}

// Additional CSS animations injected via JavaScript
const additionalStyles = `
    @keyframes labelFloat {
        0% { transform: translateY(0); }
        100% { transform: translateY(-5px); }
    }

    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }

    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-15px); }
    }

    @keyframes bigSmile {
        0%, 100% { 
            width: 22px; 
            border-width: 3px; 
            border-color: #d35400;
        }
        50% { 
            width: 30px; 
            border-width: 5px; 
            border-color: #e67e22;
        }
    }

    @keyframes fastBlink {
        0%, 100% { transform: scaleY(1); }
        50% { transform: scaleY(0.1); }
    }

    @keyframes wave {
        0%, 100% { transform: rotate(-20deg); }
        25% { transform: rotate(-45deg); }
        50% { transform: rotate(-20deg); }
        75% { transform: rotate(-45deg); }
    }

    .field-error {
        animation: fadeInError 0.3s ease-out;
    }

    @keyframes fadeInError {
        0% { opacity: 0; transform: translateY(-10px); }
        100% { opacity: 1; transform: translateY(0); }
    }
`;

// Inject additional styles
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new AnimatedLogin();
});

// Handle window resize
window.addEventListener('resize', () => {
    const particles = document.querySelectorAll('.particle');
    particles.forEach(particle => particle.remove());
});

// Accessibility: Skip animation for users who prefer reduced motion
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.documentElement.style.setProperty('--animation-duration', '0s');
}
