let toastTimer;
function showToast(msg, type = 'default') {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = 'toast show' + (type !== 'default' ? ' toast-' + type : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 3000);
}

function setRole(role) {
  document.querySelectorAll('.role-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.role === role);
  });
  const roleInput = document.getElementById('role-input');
  if (roleInput) roleInput.value = role;
}

function togglePass(inputId = 'login-pass') {
  const inp = document.getElementById(inputId);
  if (!inp) return;
  inp.type = inp.type === 'password' ? 'text' : 'password';
}

function validateRegisterForm() {
  const pw  = document.getElementById('password').value;
  const cpw = document.getElementById('confirm_password').value;
  if (pw !== cpw) {
    alert('Passwords do not match. Please try again.');
    return false;
  }
  if (pw.length < 6) {
    alert('Password must be at least 6 characters.');
    return false;
  }
  return true;
}
function submitAction(form) {
  // Allow normal POST if fetch not available
  if (!window.fetch) { form.submit(); return; }
  fetch(form.action, {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
  }).then(r => {
    if (r.redirected) { window.location.href = r.url; }
    else { window.location.reload(); }
  }).catch(() => form.submit());
}

let pendingDeleteForm = null;

function openDeleteModal(formEl) {
  pendingDeleteForm = formEl;
  const overlay = document.getElementById('delete-modal');
  if (overlay) overlay.classList.add('open');
}

function closeDeleteModal() {
  pendingDeleteForm = null;
  const overlay = document.getElementById('delete-modal');
  if (overlay) overlay.classList.remove('open');
}

function confirmDelete() {
  if (pendingDeleteForm) pendingDeleteForm.submit();
  closeDeleteModal();
}

document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('delete-modal');
  if (overlay) {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) closeDeleteModal();
    });
  }

  document.querySelectorAll('.alert').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.5s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 500);
    }, 4000);
  });
});
