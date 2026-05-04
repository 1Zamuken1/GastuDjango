/* =============================================================
   gastu_alerts.js  —  GastuApp
   Motor universal de alertas y notificaciones basado en SweetAlert2
   ============================================================= */

window.GastuAlerts = {
    
    // Configuración base para el modo "Modal" (al centro de la pantalla)
    _baseModal: {
        background: '#ffffff',
        backdrop: `rgba(15, 23, 42, 0.4)`,
        confirmButtonColor: '#10b981', // Verde Gastu
        cancelButtonColor: '#64748b',  // Gris pizarra
        confirmButtonText: 'Confirmar',
        cancelButtonText: 'Cancelar',
        buttonsStyling: true,
        customClass: {
            popup: 'gastu-swal-popup',
            title: 'gastu-swal-title',
            htmlContainer: 'gastu-swal-html',
            confirmButton: 'gastu-swal-confirm',
            cancelButton: 'gastu-swal-cancel',
        }
    },

    // Configuración base para el modo "Toast" (esquina superior derecha, auto-cierre)
    _baseToast: {
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 4000,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.addEventListener('mouseenter', Swal.stopTimer)
            toast.addEventListener('mouseleave', Swal.resumeTimer)
        },
        customClass: {
            popup: 'gastu-toast-popup',
            title: 'gastu-toast-title',
        }
    },

    /**
     * Muestra un Toast de éxito
     * @param {string} mensaje 
     */
    toastSuccess: function(mensaje) {
        return Swal.fire({
            ...this._baseToast,
            icon: 'success',
            title: mensaje,
            background: '#ecfdf5', // Verde muy claro
            color: '#065f46',      // Texto verde oscuro
            iconColor: '#10b981'   // Icono verde Gastu
        });
    },

    /**
     * Muestra un Toast de error
     * @param {string} mensaje 
     */
    toastError: function(mensaje) {
        return Swal.fire({
            ...this._baseToast,
            icon: 'error',
            title: mensaje,
            background: '#fef2f2', // Rojo muy claro
            color: '#991b1b',      // Texto rojo oscuro
            iconColor: '#ef4444'   // Icono rojo Gastu
        });
    },

    /**
     * Muestra un Toast de advertencia / info
     * @param {string} mensaje 
     */
    toastInfo: function(mensaje) {
        return Swal.fire({
            ...this._baseToast,
            icon: 'info',
            title: mensaje,
            background: '#eff6ff',
            color: '#1e3a8a',
            iconColor: '#3b82f6'
        });
    },

    /**
     * Muestra un Modal de Confirmación (Pregunta)
     * @param {string} titulo 
     * @param {string} texto 
     * @param {string} confirmText 
     * @returns {Promise<boolean>} Retorna true si el usuario confirmó
     */
    confirmar: async function(titulo, texto, confirmText = 'Sí, continuar') {
        const result = await Swal.fire({
            ...this._baseModal,
            title: titulo,
            text: texto,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: confirmText,
        });
        return result.isConfirmed;
    },

    /**
     * Muestra un Modal de Éxito o Información (Centro)
     * @param {string} titulo 
     * @param {string} texto 
     * @param {string} tipo 'success' | 'error' | 'info' | 'warning'
     */
    modal: function(titulo, texto, tipo = 'success') {
        return Swal.fire({
            ...this._baseModal,
            title: titulo,
            text: texto,
            icon: tipo,
            showCancelButton: false,
            confirmButtonText: 'Entendido',
        });
    }
};

// Insertar CSS dinámico para las clases de personalización de GastuAlerts
(function() {
    const style = document.createElement('style');
    style.innerHTML = `
        /* Estilos para Modal */
        .gastu-swal-popup {
            border-radius: 20px !important;
            padding: 24px !important;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
            font-family: 'DM Sans', sans-serif !important;
        }
        .gastu-swal-title {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 800 !important;
            color: #0f172a !important;
            font-size: 1.5rem !important;
        }
        .gastu-swal-html {
            color: #475569 !important;
            font-size: 0.95rem !important;
        }
        .gastu-swal-confirm, .gastu-swal-cancel {
            border-radius: 10px !important;
            font-weight: 600 !important;
            padding: 10px 24px !important;
            transition: all 0.2s ease !important;
        }
        .gastu-swal-confirm {
            box-shadow: 0 4px 10px rgba(16, 185, 129, 0.2) !important;
        }
        .gastu-swal-confirm:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 15px rgba(16, 185, 129, 0.3) !important;
        }
        
        /* Estilos para Toast */
        .gastu-toast-popup {
            border-radius: 12px !important;
            padding: 12px 16px !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
            font-family: 'DM Sans', sans-serif !important;
            margin-top: 10px !important;
            margin-right: 10px !important;
        }
        .gastu-toast-title {
            font-size: 0.9rem !important;
            font-weight: 600 !important;
        }
    `;
    document.head.appendChild(style);
})();
