// Funções utilitárias compartilhadas para o admin

// Formatar moeda
function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor || 0);
}

// Formatar data/hora
function formatarDataHora(isoString) {
    const data = new Date(isoString);
    return data.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatarData(isoString) {
    const data = new Date(isoString);
    return data.toLocaleDateString('pt-BR', {
        weekday: 'long',
        day: '2-digit',
        month: '2-digit'
    });
}

function formatarHora(isoString) {
    const data = new Date(isoString);
    return data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

// Status badge
function getStatusBadge(status) {
    const config = {
        'pendente': { class: 'warning', label: 'Pendente' },
        'confirmado': { class: 'success', label: 'Confirmado' },
        'em_andamento': { class: 'primary', label: 'Em andamento' },
        'concluido': { class: 'secondary', label: 'Concluído' },
        'cancelado': { class: 'danger', label: 'Cancelado' },
        'nao_compareceu': { class: 'dark', label: 'Não compareceu' }
    };
    const c = config[status] || { class: 'secondary', label: status };
    return `<span class="badge bg-${c.class}">${c.label}</span>`;
}

// Toast notification
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1080';
    document.body.appendChild(container);
    return container;
}

// Confirm modal
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Loading state
function setLoading(btn, loading = true) {
    if (loading) {
        btn.disabled = true;
        btn.dataset.originalHtml = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Carregando...';
    } else {
        btn.disabled = false;
        btn.innerHTML = btn.dataset.originalHtml || btn.innerHTML;
    }
}

// API helper
const api = {
    async get(url) {
        const resp = await axios.get(url);
        return resp.data;
    },
    async post(url, data) {
        const resp = await axios.post(url, data);
        return resp.data;
    },
    async put(url, data) {
        const resp = await axios.put(url, data);
        return resp.data;
    },
    async patch(url, data) {
        const resp = await axios.patch(url, data);
        return resp.data;
    },
    async delete(url) {
        const resp = await axios.delete(url);
        return resp.data;
    }
};

// Exportar para uso global
window.AdminUtils = {
    formatarMoeda,
    formatarDataHora,
    formatarData,
    formatarHora,
    getStatusBadge,
    showToast,
    confirmAction,
    setLoading,
    api
};