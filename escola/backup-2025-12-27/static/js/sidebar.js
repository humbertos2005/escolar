// ====================================================================
// GERENCIAMENTO DO MENU LATERAL (SIDEBAR) - MOBILE E DESKTOP
// ====================================================================

document.addEventListener('DOMContentLoaded', function() {
    
    // Elementos
    const sidebar = document.getElementById('sidebar');
    const navbarToggler = document.querySelector('.navbar-toggler');
    const mainContent = document.querySelector('.main-content');
    
    // Criar overlay para mobile
    let overlay = document.querySelector('.sidebar-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        document.body.appendChild(overlay);
    }
    
    // Toggle sidebar no mobile
    if (navbarToggler) {
        navbarToggler.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }
    
    // Fechar sidebar ao clicar no overlay
    overlay.addEventListener('click', function() {
        closeSidebar();
    });
    
    // Fechar sidebar ao clicar em um link (apenas mobile)
    if (sidebar && window.innerWidth <= 768) {
        const sidebarLinks = sidebar.querySelectorAll('.nav-link, .menu-link');
        sidebarLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    closeSidebar();
                }
            });
        });
    }
    
    // Funções auxiliares
    function toggleSidebar() {
        if (sidebar.classList.contains('show')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }
    
    function openSidebar() {
        sidebar.classList.add('show');
        overlay.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
    
    function closeSidebar() {
        sidebar.classList.remove('show');
        overlay.classList.remove('show');
        document.body.style.overflow = '';
    }
    
    // Ajustar ao redimensionar janela
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if (window.innerWidth > 768) {
                // Desktop - garantir que sidebar esteja visível
                closeSidebar();
                document.body.style.overflow = '';
            }
        }, 250);
    });
    
    // Dropdown do usuário no navbar
    const dropdownToggle = document.querySelector('.dropdown-toggle');
    const dropdownMenu = document.querySelector('.dropdown-menu');
    
    if (dropdownToggle && dropdownMenu) {
        dropdownToggle.addEventListener('click', function(e) {
            e.preventDefault();
            dropdownMenu.classList.toggle('show');
        });
        
        // Fechar dropdown ao clicar fora
        document.addEventListener('click', function(e) {
            if (!dropdownToggle.contains(e.target) && !dropdownMenu.contains(e.target)) {
                dropdownMenu.classList.remove('show');
            }
        });
    }
    
    // Destacar item ativo do menu
    highlightActiveMenuItem();
    
    function highlightActiveMenuItem() {
        const currentPath = window.location.pathname;
        const menuLinks = document.querySelectorAll('.sidebar .nav-link, .sidebar .menu-link');
        
        menuLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && currentPath.includes(href) && href !== '/') {
                link.classList.add('active');
                
                // Expandir seção pai se existir
                const parentSection = link.closest('.menu-section');
                if (parentSection) {
                    parentSection.classList.add('active');
                }
            }
        });
    }
    
    // Garantir que o conteúdo não sobreponha o navbar
    function adjustContentMargin() {
        const navbar = document.querySelector('.navbar');
        if (navbar && mainContent) {
            const navbarHeight = navbar.offsetHeight;
            mainContent.style.marginTop = navbarHeight + 'px';
        }
    }
    
    // Executar ajuste inicial
    adjustContentMargin();
    
    // Reajustar ao carregar imagens ou mudar tamanho
    window.addEventListener('load', adjustContentMargin);
    window.addEventListener('resize', adjustContentMargin);
    
    // Scroll suave para links âncora
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = this.getAttribute('href');
            if (target !== '#' && target !== '') {
                const targetElement = document.querySelector(target);
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
    
    // Adicionar classe para indicar que JS está carregado
    document.body.classList.add('js-loaded');
    
    console.log('✓ Sidebar e navegação inicializados com sucesso!');
});

// Função global para toggle programático (se necessário)
function toggleSidebarGlobal() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('show');
        const overlay = document.querySelector('.sidebar-overlay');
        if (overlay) {
            overlay.classList.toggle('show');
        }
    }
}