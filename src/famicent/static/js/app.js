/**
 * FamiCent — Main JavaScript (app.js)
 * ES6+, vanilla JS only (R34, R35).
 * Handles: CSRF injection, session timeout, modals, account/payment CRUD,
 *          admin password banner, flash message dismissal.
 */

'use strict';

// ============================================================
// 1. CSRF Token Helper
// ============================================================

/**
 * Get the CSRF token stored in the hidden meta tag.
 * @returns {string}
 */
const getCsrfToken = () => {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
};

/**
 * Perform a POST fetch with CSRF token pre-injected into FormData or JSON body.
 * @param {string} url
 * @param {FormData|Object} data
 * @returns {Promise<Response>}
 */
const postJson = async (url, data = {}) => {
  const formData = data instanceof FormData ? data : (() => {
    const fd = new FormData();
    Object.entries(data).forEach(([k, v]) => fd.append(k, v));
    return fd;
  })();
  formData.set('csrf_token', getCsrfToken());
  return fetch(url, { method: 'POST', body: formData });
};

// ============================================================
// 2. Flash Message Dismissal
// ============================================================

const initFlashMessages = () => {
  const container = document.getElementById('flash-container');
  if (!container) return;

  // Auto-dismiss after 4 seconds
  Array.from(container.children).forEach(msg => {
    setTimeout(() => msg.remove(), 4000);
  });
};

// ============================================================
// 3. Session Timeout Counter (FR-SEC-05 / R23)
// ============================================================

let sessionTimer = null;

const getSessionTimeoutMs = () => {
  const meta = document.querySelector('meta[name="session-timeout"]');
  const seconds = meta ? parseInt(meta.getAttribute('content'), 10) : 300;
  return (isNaN(seconds) ? 300 : seconds) * 1000;
};

const resetSessionTimer = () => {
  clearTimeout(sessionTimer);
  sessionTimer = setTimeout(() => {
    // Session expired — redirect to login
    window.location.href = '/login?expired=1';
  }, getSessionTimeoutMs());
};

const initSessionTimer = () => {
  if (!document.querySelector('.app-shell')) return; // only inside authenticated pages

  const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
  events.forEach(e => document.addEventListener(e, resetSessionTimer, { passive: true }));
  resetSessionTimer();
};

// ============================================================
// 4. Modal Manager
// ============================================================

/**
 * Open a modal overlay by ID.
 * @param {string} id - The overlay element's id.
 */
const openModal = (id) => {
  const overlay = document.getElementById(id);
  if (!overlay) return;
  overlay.classList.add('active');
  overlay.querySelector('.modal')?.focus();
};

/**
 * Close a modal overlay by ID.
 * @param {string} id
 */
const closeModal = (id) => {
  const overlay = document.getElementById(id);
  if (!overlay) return;
  overlay.classList.remove('active');
};

const initModals = () => {
  // Overlays should not close when clicking outside the modal dialog box, preventing misclick dismissals.

  // Close buttons
  document.querySelectorAll('[data-modal-close]').forEach(btn => {
    btn.addEventListener('click', () => {
      const modalId = btn.closest('.modal-overlay')?.id;
      if (modalId) closeModal(modalId);
    });
  });

  // Open triggers
  document.querySelectorAll('[data-modal-open]').forEach(btn => {
    btn.addEventListener('click', () => openModal(btn.dataset.modalOpen));
  });

  // ESC key
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.active').forEach(overlay => {
        overlay.classList.remove('active');
      });
    }
  });
};

// ============================================================
// 5. Password Toggle Visibility
// ============================================================

const initPasswordToggles = () => {
  document.querySelectorAll('.password-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.closest('.password-field')?.querySelector('input');
      if (!input) return;
      input.type = input.type === 'password' ? 'text' : 'password';
      btn.textContent = input.type === 'password' ? '👁' : '🙈';
    });
  });

  // Handle portal credentials visibility and auto-masking after 5 seconds
  document.querySelectorAll('.btn-toggle-field-pwd').forEach(btn => {
    let timeoutId = null;
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = btn.dataset.pwdToggle;
      const input = document.getElementById(targetId);
      if (!input) return;

      if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈';
        
        // Auto-mask password after 5 seconds (5000ms)
        if (timeoutId) clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          input.type = 'password';
          btn.textContent = '👁️';
        }, 5000);
      } else {
        input.type = 'password';
        btn.textContent = '👁️';
        if (timeoutId) clearTimeout(timeoutId);
      }
    });
  });
};

// ============================================================
// 6. Admin Password Banner
// ============================================================

const initPasswordBanner = () => {
  const banner = document.getElementById('password-banner');
  if (!banner) return;

  // Manual Change Password
  const changeBtn = document.getElementById('banner-change-password-btn');
  if (changeBtn) {
    changeBtn.addEventListener('click', () => openModal('change-password-modal'));
  }

  // Generate Password
  const generateBtn = document.getElementById('banner-generate-password-btn');
  if (generateBtn) {
    generateBtn.addEventListener('click', async () => {
      generateBtn.disabled = true;
      generateBtn.textContent = 'Generating…';
      try {
        const resp = await postJson('/generate-password', {});
        const data = await resp.json();
        if (data.success) {
          const display = document.getElementById('generated-password-display');
          if (display) {
            display.textContent = data.password;
            display.closest('#generated-password-modal') && openModal('generated-password-modal');
          }
          openModal('generated-password-modal');
          banner.remove();
        } else {
          alert('Failed to generate password: ' + (data.error || 'Unknown error'));
        }
      } catch (err) {
        alert('Network error. Please try again.');
      } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Password';
      }
    });
  }

  // Change Password form submission
  const changeForm = document.getElementById('change-password-form');
  if (changeForm) {
    changeForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(changeForm);
      const errorEl = document.getElementById('change-password-error');
      try {
        const resp = await postJson('/change-password', formData);
        const data = await resp.json();
        if (data.success) {
          closeModal('change-password-modal');
          banner.remove();
          showFlash('Password changed successfully!', 'success');
        } else {
          if (errorEl) errorEl.textContent = data.error || 'Failed to change password.';
        }
      } catch (err) {
        if (errorEl) errorEl.textContent = 'Network error. Please try again.';
      }
    });
  }

  // Copy generated password
  const copyBtn = document.getElementById('copy-generated-password-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const text = document.getElementById('generated-password-display')?.textContent;
      if (text) {
        navigator.clipboard.writeText(text).then(() => {
          copyBtn.textContent = '✓ Copied!';
          setTimeout(() => (copyBtn.textContent = 'Copy'), 2000);
        });
      }
    });
  }
};

// ============================================================
// 7. Account CRUD
// ============================================================

const initAccountsPage = () => {
  // Create account form
  const createForm = document.getElementById('create-account-form');
  if (createForm) {
    createForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById('create-account-error');
      const formData = new FormData(createForm);
      try {
        const resp = await postJson('/accounts/create', formData);
        const data = await resp.json();
        if (data.success) {
          window.location.reload();
        } else {
          if (errorEl) errorEl.textContent = data.error || 'Failed to create account.';
        }
      } catch (err) {
        if (errorEl) errorEl.textContent = 'Network error.';
      }
    });
  }
  // Toggle Year visibility on Next Due Date based on Billing Cycle selection
  const setupBillingCycleToggle = (cycleId, yyyyId, mmId, ddId, weekdayId) => {
    const cycleSelect = document.getElementById(cycleId);
    const yInput = document.getElementById(yyyyId);
    const mInput = document.getElementById(mmId);
    const dInput = document.getElementById(ddId);
    const weekdaySelect = document.getElementById(weekdayId);
    if (!cycleSelect) return;

    const toggleFields = () => {
      const val = cycleSelect.value;
      const dateWrapper = yInput?.closest('.date-input-wrapper');
      
      if (val === 'weekly') {
        // Hide standard YYYY-MM-DD inputs completely
        if (dateWrapper) dateWrapper.style.display = 'none';
        // Show weekday dropdown
        if (weekdaySelect) {
          weekdaySelect.style.display = '';
          weekdaySelect.setAttribute('name', 'next_due_date');
        }
        if (yInput) {
          yInput.style.display = 'none';
          yInput.removeAttribute('required');
        }
      } else if (val === 'monthly') {
        // Show standard date inputs wrapper
        if (dateWrapper) dateWrapper.style.display = '';
        // Hide weekday dropdown
        if (weekdaySelect) {
          weekdaySelect.style.display = 'none';
          weekdaySelect.removeAttribute('name');
        }
        
        if (yInput) {
          yInput.style.display = 'none';
          if (yInput.previousElementSibling && yInput.previousElementSibling.tagName === 'SPAN') {
            yInput.previousElementSibling.style.display = 'none';
          }
          if (yInput.nextElementSibling && yInput.nextElementSibling.tagName === 'SPAN') {
            yInput.nextElementSibling.style.display = 'none';
          }
          yInput.removeAttribute('required');
        }
      } else {
        // Show standard date inputs wrapper
        if (dateWrapper) dateWrapper.style.display = '';
        // Hide weekday dropdown
        if (weekdaySelect) {
          weekdaySelect.style.display = 'none';
          weekdaySelect.removeAttribute('name');
        }
        
        if (yInput) {
          yInput.style.display = '';
          if (yInput.previousElementSibling && yInput.previousElementSibling.tagName === 'SPAN') {
            yInput.previousElementSibling.style.display = '';
          }
          if (yInput.nextElementSibling && yInput.nextElementSibling.tagName === 'SPAN') {
            yInput.nextElementSibling.style.display = '';
          }
        }
      }
    };
    cycleSelect.addEventListener('change', toggleFields);
    toggleFields();
  };

  setupBillingCycleToggle('create-billing-cycle', 'create-next-due-yyyy', 'create-next-due-mm', 'create-next-due-dd', 'create-next-due-weekday');
  setupBillingCycleToggle('edit-billing-cycle', 'edit-next-due-yyyy', 'edit-next-due-mm', 'edit-next-due-dd', 'edit-next-due-weekday');
  // Edit account
  document.querySelectorAll('[data-edit-account]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const accountId = btn.dataset.editAccount;
      try {
        const resp = await fetch(`/accounts/${accountId}`);
        const account = await resp.json();
        _populateEditForm(account);
        openModal('edit-account-modal');
      } catch (err) {
        console.error('Failed to load account', err);
      }
    });
  });

  // Edit form submit
  const editForm = document.getElementById('edit-account-form');
  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const accountId = editForm.dataset.accountId;
      const errorEl = document.getElementById('edit-account-error');
      try {
        const resp = await postJson(`/accounts/${accountId}/update`, new FormData(editForm));
        const data = await resp.json();
        if (data.success) {
          window.location.reload();
        } else {
          if (errorEl) errorEl.textContent = data.error || 'Failed to update account.';
        }
      } catch (err) {
        if (errorEl) errorEl.textContent = 'Network error.';
      }
    });
  }

  // Delete account
  document.querySelectorAll('[data-delete-account]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const accountId = btn.dataset.deleteAccount;
      if (!confirm('Delete this account and all its payments? This cannot be undone.')) return;
      try {
        const resp = await postJson(`/accounts/${accountId}/delete`, {});
        const data = await resp.json();
        if (data.success) window.location.reload();
      } catch (err) {
        console.error('Delete failed', err);
      }
    });
  });

  // Category filter pills
  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const category = pill.dataset.category;
      const url = new URL(window.location.href);
      if (category === 'all') {
        url.searchParams.delete('category');
      } else {
        url.searchParams.set('category', category);
      }
      window.location.href = url.toString();
    });
  });
};

const _populateEditForm = (account) => {
  const form = document.getElementById('edit-account-form');
  if (!form) return;
  form.dataset.accountId = account.id;
  form.querySelector('[name="name"]').value = account.name || '';
  form.querySelector('[name="category"]').value = account.category || '';
  form.querySelector('[name="provider"]').value = account.provider || '';
  form.querySelector('[name="balance"]').value = account.balance ?? '';
  form.querySelector('[name="billing_cycle"]').value = account.billing_cycle || '';
  form.querySelector('[name="next_due_date"]').value = account.next_due_date || '';
  form.querySelector('[name="website_url"]').value = account.website_url || '';
  form.querySelector('[name="website_username"]').value = account.website_username || '';
  form.querySelector('[name="website_password"]').value = account.website_password || '';
  form.querySelector('[name="notes"]').value = account.notes || '';
  
  // Populate the split date parts
  const yEl = document.getElementById('edit-next-due-yyyy');
  const mEl = document.getElementById('edit-next-due-mm');
  const dEl = document.getElementById('edit-next-due-dd');
  if (yEl && mEl && dEl) {
    if (account.next_due_date && account.next_due_date.includes('-')) {
      const parts = account.next_due_date.split('-');
      if (parts.length === 2) {
        // MM-DD format (monthly)
        yEl.value = '';
        mEl.value = parts[0] || '';
        dEl.value = parts[1] || '';
      } else if (parts.length === 3) {
        // YYYY-MM-DD format (standard)
        yEl.value = parts[0] || '';
        mEl.value = parts[1] || '';
        dEl.value = parts[2] || '';
      } else {
        yEl.value = '';
        mEl.value = '';
        dEl.value = '';
      }
    } else {
      yEl.value = '';
      mEl.value = '';
      dEl.value = '';
    }
  }

  // Trigger billing cycle visibility adjustment
  const editBillingCycle = document.getElementById('edit-billing-cycle');
  if (editBillingCycle) {
    editBillingCycle.dispatchEvent(new Event('change'));
    
    // If weekly, select weekday matching next_due_date value
    if (account.billing_cycle === 'weekly' && account.next_due_date) {
      const weekdaySelect = document.getElementById('edit-next-due-weekday');
      if (weekdaySelect) {
        weekdaySelect.value = account.next_due_date;
      }
    }
  }
};

// ============================================================
// 8. Payment CRUD
// ============================================================

const initPaymentsPage = () => {
  const recordForm = document.getElementById('record-payment-form');
  if (recordForm) {
    recordForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById('record-payment-error');
      try {
        const resp = await postJson('/payments/record', new FormData(recordForm));
        const data = await resp.json();
        if (data.success) {
          window.location.reload();
        } else {
          if (errorEl) errorEl.textContent = data.error || 'Failed to record payment.';
        }
      } catch (err) {
        if (errorEl) errorEl.textContent = 'Network error.';
      }
    });
  }

  // Edit payment click
  document.querySelectorAll('[data-edit-payment]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const paymentId = btn.dataset.editPayment;
      try {
        const resp = await fetch(`/payments/${paymentId}`);
        const payment = await resp.json();
        
        const form = document.getElementById('edit-payment-form');
        if (!form) return;
        form.dataset.paymentId = payment.id;
        form.querySelector('[name="account_id"]').value = payment.account_id || '';
        form.querySelector('[name="amount"]').value = payment.amount ?? '';
        form.querySelector('[name="method"]').value = payment.method || '';
        form.querySelector('[name="payment_date"]').value = payment.payment_date || '';
        
        // Populate the split date parts
        const yEl = document.getElementById('edit-payment-date-yyyy');
        const mEl = document.getElementById('edit-payment-date-mm');
        const dEl = document.getElementById('edit-payment-date-dd');
        if (yEl && mEl && dEl) {
          if (payment.payment_date && payment.payment_date.includes('-')) {
            const parts = payment.payment_date.split('-');
            yEl.value = parts[0] || '';
            mEl.value = parts[1] || '';
            dEl.value = parts[2] || '';
          } else {
            yEl.value = '';
            mEl.value = '';
            dEl.value = '';
          }
        }
        
        openModal('edit-payment-modal');
      } catch (err) {
        console.error('Failed to load payment details', err);
      }
    });
  });

  // Edit payment form submit
  const editPaymentForm = document.getElementById('edit-payment-form');
  if (editPaymentForm) {
    editPaymentForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const paymentId = editPaymentForm.dataset.paymentId;
      const errorEl = document.getElementById('edit-payment-error');
      try {
        const resp = await postJson(`/payments/${paymentId}/update`, new FormData(editPaymentForm));
        const data = await resp.json();
        if (data.success) {
          window.location.reload();
        } else {
          if (errorEl) errorEl.textContent = data.error || 'Failed to update payment.';
        }
      } catch (err) {
        if (errorEl) errorEl.textContent = 'Network error.';
      }
    });
  }

  document.querySelectorAll('[data-delete-payment]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const paymentId = btn.dataset.deletePayment;
      if (!confirm('Delete this payment record?')) return;
      try {
        const resp = await postJson(`/payments/${paymentId}/delete`, {});
        const data = await resp.json();
        if (data.success) window.location.reload();
      } catch (err) {
        console.error('Delete failed', err);
      }
    });
  });

  // Account filter
  const filterSelect = document.getElementById('payment-account-filter');
  if (filterSelect) {
    filterSelect.addEventListener('change', () => {
      const url = new URL(window.location.href);
      if (filterSelect.value) {
        url.searchParams.set('account_id', filterSelect.value);
      } else {
        url.searchParams.delete('account_id');
      }
      window.location.href = url.toString();
    });
  }
};

// ============================================================
// 9. Settings Page
// ============================================================

const initSettingsPage = () => {
  const resetMfaBtn = document.getElementById('reset-mfa-btn');
  if (resetMfaBtn) {
    resetMfaBtn.addEventListener('click', async () => {
      try {
        const resp = await postJson('/settings/mfa/reset', {});
        const data = await resp.json();
        if (data.success) {
          const qrImg = document.getElementById('mfa-reset-qr');
          const secretEl = document.getElementById('mfa-reset-secret');
          if (qrImg) qrImg.src = data.qr_data;
          if (secretEl) secretEl.textContent = data.secret;
          openModal('mfa-reset-modal');
        }
      } catch (err) {
        console.error('MFA reset failed', err);
      }
    });
  }

  const confirmForm = document.getElementById('mfa-confirm-form');
  if (confirmForm) {
    confirmForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById('mfa-confirm-error');
      try {
        const resp = await postJson('/settings/mfa/confirm', new FormData(confirmForm));
        const data = await resp.json();
        if (data.success) {
          closeModal('mfa-reset-modal');
          showFlash('MFA re-enrolled successfully!', 'success');
        } else {
          if (errorEl) errorEl.textContent = data.error || 'Invalid code.';
        }
      } catch (err) {
        if (errorEl) errorEl.textContent = 'Network error.';
      }
    });
  }

  const updateProfileForm = document.getElementById('update-profile-form');
  if (updateProfileForm) {
    updateProfileForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById('update-profile-error');
      const submitBtn = document.getElementById('save-profile-btn');
      if (errorEl) errorEl.textContent = '';
      if (submitBtn) submitBtn.disabled = true;

      try {
        const resp = await postJson('/settings/update-profile', new FormData(updateProfileForm));
        const data = await resp.json();
        if (data.success) {
          showFlash('Profile settings saved successfully!', 'success');
          setTimeout(() => window.location.reload(), 1000);
        } else {
          if (errorEl) errorEl.textContent = data.error || 'Failed to save settings.';
          if (submitBtn) submitBtn.disabled = false;
        }
      } catch (err) {
        if (errorEl) errorEl.textContent = 'Network error.';
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }
};

// ============================================================
// 9.5 Users Management Page
// ============================================================

const initUsersPage = () => {
  const createUserForm = document.getElementById('create-user-form');
  const usernameInput = document.getElementById('user-username');
  const passwordInput = document.getElementById('user-password');
  let passwordManuallyEdited = false;

  if (usernameInput && passwordInput) {
    usernameInput.addEventListener('input', () => {
      if (!passwordManuallyEdited) {
        const val = usernameInput.value.trim().toLowerCase();
        passwordInput.value = val ? val + '123' : '';
      }
    });

    passwordInput.addEventListener('input', () => {
      passwordManuallyEdited = passwordInput.value.length > 0;
    });
  }

  if (createUserForm) {
    createUserForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById('create-user-error');
      const submitBtn = document.getElementById('confirm-create-user-btn');
      if (errorEl) errorEl.textContent = '';
      if (submitBtn) submitBtn.disabled = true;
      try {
        const resp = await postJson('/users/create', new FormData(createUserForm));
        const data = await resp.json();
        if (data.success) {
          window.location.reload();
        } else {
          if (errorEl) errorEl.textContent = data.error || 'Failed to create user.';
          if (submitBtn) submitBtn.disabled = false;
        }
      } catch (err) {
        if (errorEl) errorEl.textContent = 'Network error.';
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  document.querySelectorAll('[data-delete-user]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const userId = btn.dataset.deleteUser;
      if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) return;
      try {
        const resp = await postJson(`/users/${userId}/delete`, {});
        const data = await resp.json();
        if (data.success) {
          window.location.reload();
        } else {
          alert(data.error || 'Failed to delete user.');
        }
      } catch (err) {
        alert('Network error.');
      }
    });
  });

  // Edit user modal trigger
  document.querySelectorAll('[data-edit-user]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const userId = btn.dataset.editUser;
      try {
        const resp = await fetch(`/users/${userId}`);
        const user = await resp.json();
        const form = document.getElementById('edit-user-form');
        if (form) {
          form.dataset.userId = user.id;
          document.getElementById('edit-user-username').value = user.username;
          document.getElementById('edit-user-profile-name').value = user.profile_name || '';
          document.getElementById('edit-user-password').value = '';
          document.getElementById('edit-user-role').value = user.role;
          document.getElementById('edit-user-session-timeout').value = user.session_timeout || 300;
          
          const roleSelect = document.getElementById('edit-user-role');
          if (roleSelect) {
            roleSelect.disabled = (user.role === 'admin');
          }
          
          const mfaCheckbox = document.getElementById('edit-user-reset-mfa');
          const enforceCheckbox = document.getElementById('edit-user-enforce-mfa');
          const mfaStatus = document.getElementById('edit-user-mfa-status');
          if (mfaCheckbox) mfaCheckbox.checked = false;
          if (enforceCheckbox) enforceCheckbox.checked = !!user.mfa_enforced;
          if (mfaStatus) {
            if (user.mfa_enabled) {
              mfaStatus.textContent = 'MFA Status: Active (Enrolled)';
              mfaStatus.style.color = 'var(--clr-success)';
            } else {
              mfaStatus.textContent = 'MFA Status: Not Enrolled (Pending next login)';
              mfaStatus.style.color = 'var(--clr-text-muted)';
            }
          }

          openModal('edit-user-modal');
        }
      } catch (err) {
        console.error('Failed to fetch user details', err);
      }
    });
  });

  // Submit edit user form
  const editUserForm = document.getElementById('edit-user-form');
  if (editUserForm) {
    editUserForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const userId = editUserForm.dataset.userId;
      const errorEl = document.getElementById('edit-user-error');
      const submitBtn = document.getElementById('confirm-edit-user-btn');
      if (errorEl) errorEl.textContent = '';
      if (submitBtn) submitBtn.disabled = true;

      try {
        const resp = await postJson(`/users/${userId}/update`, new FormData(editUserForm));
        const data = await resp.json();
        if (data.success) {
          window.location.reload();
        } else {
          if (errorEl) errorEl.textContent = data.error || 'Failed to update user.';
          if (submitBtn) submitBtn.disabled = false;
        }
      } catch (err) {
        if (errorEl) errorEl.textContent = 'Network error.';
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }
};

// ============================================================
// 9.6 DB Looker Page
// ============================================================

const initDbViewerPage = () => {
  const queryForm = document.getElementById('custom-query-form');
  if (queryForm) {
    // Add Ctrl + Enter shortcut support inside textarea
    const queryInput = document.getElementById('sql-query');
    if (queryInput) {
      queryInput.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
          e.preventDefault();
          queryForm.requestSubmit(); // Triggers submit handler validation and post
        }
      });
    }

    queryForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById('query-error-display');
      const submitBtn = document.getElementById('run-query-btn');
      const wrapper = document.getElementById('results-table-wrapper');
      const titleEl = document.getElementById('results-title');

      if (errorEl) errorEl.textContent = '';
      if (submitBtn) submitBtn.disabled = true;

      try {
        const resp = await postJson('/dbviewer/query', new FormData(queryForm));
        const data = await resp.json();
        
        if (submitBtn) submitBtn.disabled = false;

        if (data.success) {
          if (titleEl) titleEl.textContent = 'Query Results';
          if (wrapper) {
            if (data.rows.length === 0) {
              wrapper.innerHTML = `
                <div class="empty-state" style="padding: var(--space-8);">
                  <div class="empty-state-icon" aria-hidden="true">🔍</div>
                  <div class="empty-state-title">No rows returned</div>
                  <p class="empty-state-text">The query executed successfully but returned 0 rows.</p>
                </div>`;
              return;
            }

            let html = `<table><thead><tr>`;
            data.columns.forEach(col => {
              html += `<th>${col}</th>`;
            });
            html += `</tr></thead><tbody>`;
            data.rows.forEach(row => {
              html += `<tr>`;
              row.forEach(cell => {
                html += `<td>${cell === null ? '<em>null</em>' : cell}</td>`;
              });
              html += `</tr>`;
            });
            html += `</tbody></table>`;
            wrapper.innerHTML = html;
          }
        } else {
          if (errorEl) errorEl.textContent = data.error || 'Failed to execute query.';
        }
      } catch (err) {
        if (errorEl) errorEl.textContent = 'Network error.';
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }
};

// ============================================================
// 10. Utility: Show a flash message programmatically
// ============================================================

/**
 * Display a temporary flash message in the flash container.
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} type
 */
const showFlash = (message, type = 'info') => {
  const container = document.getElementById('flash-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `flash-message flash-${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
};

// ============================================================
// 11. Sidebar Mobile Toggle
// ============================================================

const initMobileNav = () => {
  const toggleBtn = document.getElementById('sidebar-toggle');
  const sidebar = document.querySelector('.sidebar');
  if (!toggleBtn || !sidebar) return;

  toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('mobile-open');
  });

  // Close on nav item click (mobile)
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => sidebar.classList.remove('mobile-open'));
  });
};

// ============================================================
// 11.5 Date Inputs Autofocus Nav
// ============================================================

const initDateAutoTab = () => {
  // Bind input listeners for all components to combine values and manage focus
  const setups = [
    { base: 'create-next-due', y: 'create-next-due-yyyy', m: 'create-next-due-mm', d: 'create-next-due-dd' },
    { base: 'edit-next-due', y: 'edit-next-due-yyyy', m: 'edit-next-due-mm', d: 'edit-next-due-dd' },
    { base: 'payment-date', y: 'payment-date-yyyy', m: 'payment-date-mm', d: 'payment-date-dd' },
    { base: 'edit-payment-date', y: 'edit-payment-date-yyyy', m: 'edit-payment-date-mm', d: 'edit-payment-date-dd' }
  ];

  setups.forEach(setup => {
    const hiddenEl = document.getElementById(setup.base);
    const yEl = document.getElementById(setup.y);
    const mEl = document.getElementById(setup.m);
    const dEl = document.getElementById(setup.d);

    if (!hiddenEl || !yEl || !mEl || !dEl) return;

    const updateHidden = () => {
      const yVal = yEl.value.trim();
      const mVal = mEl.value.trim();
      const dVal = dEl.value.trim();
      
      // Determine if this is create or edit, and get its billing cycle
      let isMonthly = false;
      const modal = yEl.closest('.modal');
      if (modal) {
        const cycleSelect = modal.querySelector('select[name="billing_cycle"]');
        if (cycleSelect && cycleSelect.value === 'monthly') {
          isMonthly = true;
        }
      }

      if (isMonthly) {
        if (mVal && dVal) {
          hiddenEl.value = `${mVal.padStart(2, '0')}-${dVal.padStart(2, '0')}`;
        } else {
          hiddenEl.value = '';
        }
      } else {
        if (yVal && mVal && dVal) {
          hiddenEl.value = `${yVal}-${mVal.padStart(2, '0')}-${dVal.padStart(2, '0')}`;
        } else {
          hiddenEl.value = '';
        }
      }
    };

    yEl.addEventListener('input', () => {
      // Clean non-digits
      yEl.value = yEl.value.replace(/\D/g, '');
      updateHidden();
      if (yEl.value.length === 4) {
        mEl.focus();
      }
    });

    mEl.addEventListener('input', () => {
      mEl.value = mEl.value.replace(/\D/g, '');
      updateHidden();
      if (mEl.value.length === 2) {
        dEl.focus();
      }
    });

    dEl.addEventListener('input', () => {
      dEl.value = dEl.value.replace(/\D/g, '');
      updateHidden();
    });

    // Auto-advance if user types and length reached on keydown/keyup
    yEl.addEventListener('keyup', (e) => {
      if (yEl.value.length === 4 && e.key !== 'Backspace' && e.key !== 'Tab') {
        mEl.focus();
      }
    });
    mEl.addEventListener('keyup', (e) => {
      if (mEl.value.length === 2 && e.key !== 'Backspace' && e.key !== 'Tab') {
        dEl.focus();
      }
    });
  });
};

// ============================================================
// 11.7 Theme Switcher Manager
// ============================================================

const initTheme = () => {
  const toggleBtn = document.getElementById('theme-toggle-btn');
  if (!toggleBtn) return;

  const getSavedTheme = () => localStorage.getItem('theme');
  const saveTheme = (theme) => localStorage.setItem('theme', theme);

  const applyTheme = (theme) => {
    if (theme === 'light') {
      document.documentElement.classList.add('light-theme');
    } else {
      document.documentElement.classList.remove('light-theme');
    }
  };

  // Event listener
  toggleBtn.addEventListener('click', () => {
    const isLight = document.documentElement.classList.contains('light-theme');
    const newTheme = isLight ? 'dark' : 'light';
    applyTheme(newTheme);
    saveTheme(newTheme);
  });
};

// ============================================================
// 11.8 Sidebar Auto-Hide (3 Minutes Idle)
// ============================================================

const initSidebarAutoHide = () => {
  const shell = document.querySelector('.app-shell');
  if (!shell) return;

  let idleTime = 0;
  const idleLimit = 180; // 3 minutes = 180 seconds

  const showSidebar = () => {
    shell.classList.remove('sidebar-hidden');
  };

  const hideSidebar = () => {
    shell.classList.add('sidebar-hidden');
  };

  const resetIdleTimer = () => {
    if (shell.classList.contains('sidebar-hidden')) {
      showSidebar();
    }
    idleTime = 0;
  };

  const events = ['mousemove', 'keypress', 'click', 'scroll', 'touchstart'];
  events.forEach(event => {
    document.addEventListener(event, resetIdleTimer, { passive: true });
  });

  setInterval(() => {
    idleTime++;
    if (idleTime >= idleLimit) {
      hideSidebar();
    }
  }, 1000);
};

// ============================================================
// 12. Init on DOM Ready
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  initFlashMessages();
  initSessionTimer();
  initModals();
  initPasswordToggles();
  initPasswordBanner();
  initMobileNav();
  initDateAutoTab();
  initTheme();
  initSidebarAutoHide();

  // Page-specific init based on body data attribute
  const page = document.body.dataset.page;
  if (page === 'accounts') initAccountsPage();
  if (page === 'payments') initPaymentsPage();
  if (page === 'settings') initSettingsPage();
  if (page === 'users') initUsersPage();
  if (page === 'dbviewer') initDbViewerPage();
});
