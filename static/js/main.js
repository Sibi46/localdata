// Mobile menu toggle
function toggleMenu() {
    const menu = document.getElementById('mobileMenu');
    if (!menu) return;
    const open = menu.classList.toggle('open');
    const button = document.querySelector('[aria-controls="mobileMenu"]');
    if (button) button.setAttribute('aria-expanded', String(open));
}

// Tab filter - categories
function showTab(type) {
    const cards = document.querySelectorAll('.cat-card');
    const buttons = document.querySelectorAll('.tab-btn');

    buttons.forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    cards.forEach(card => {
        if (type === 'all') {
            card.style.display = 'block';
        } else {
            card.style.display = card.dataset.type === type ? 'block' : 'none';
        }
    });
}

// Hero filter by category
function filterCategory(type) {
    showTab(type);
    document.getElementById('categories').scrollIntoView({ behavior: 'smooth' });
}

// Search jobs
function searchJobs() {
    const job = document.getElementById('heroJobInput').value.trim();
    const location = document.getElementById('heroLocationInput').value.trim();
    if (job || location) {
        window.location.href = `/jobs?q=${encodeURIComponent(job)}&location=${encodeURIComponent(location)}`;
    }
}

// Enter key search
document.addEventListener('DOMContentLoaded', function () {
    const inputs = document.querySelectorAll('.hero-search input');
    inputs.forEach(input => {
        input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') searchJobs();
        });
    });

    // Show choose-type modal on page load (only if not seen before)
    const chooseModal = document.getElementById('chooseTypeModal');
    if (chooseModal && !sessionStorage.getItem('modalSeen')) {
        chooseModal.classList.remove('hidden');
    }
});

function closeModal() {
    const m = document.getElementById('chooseTypeModal');
    if (m) m.classList.add('hidden');
    sessionStorage.setItem('modalSeen', '1');
}

// Close modal when clicking outside the box
document.addEventListener('click', function(e) {
    const modal = document.getElementById('chooseTypeModal');
    if (modal && e.target === modal) {
        closeModal();
    }
});
