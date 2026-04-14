// Tiny UI helpers for PLCtracker.
// Keeps things working without a framework beyond Alpine.js.

(function () {
  // 1. Mobile sidebar drawer toggle
  window.togglePlctSidebar = function () {
    document.body.classList.toggle('sidebar-open');
  };
  document.addEventListener('click', function (e) {
    if (e.target && e.target.matches('.sidebar-backdrop')) {
      document.body.classList.remove('sidebar-open');
    }
  });

  // 2. Row-click navigation on the products data-table
  document.addEventListener('click', function (e) {
    var tr = e.target.closest('tr.row-link');
    if (!tr) return;
    // Don't hijack clicks inside links/buttons/forms
    if (e.target.closest('a, button, form, input, select, textarea, label')) return;
    var href = tr.getAttribute('data-href');
    if (href) window.location.href = href;
  });

  // 3. Drag-and-drop visual for the upload dropzone
  document.addEventListener('dragover', function (e) {
    if (e.target.closest('.dropzone')) {
      e.preventDefault();
      e.target.closest('.dropzone').classList.add('is-drag');
    }
  });
  document.addEventListener('dragleave', function (e) {
    if (e.target.closest('.dropzone')) {
      e.target.closest('.dropzone').classList.remove('is-drag');
    }
  });
  document.addEventListener('drop', function (e) {
    var dz = e.target.closest('.dropzone');
    if (!dz) return;
    e.preventDefault();
    dz.classList.remove('is-drag');
    var inp = dz.querySelector('input[type=file]');
    if (inp && e.dataTransfer && e.dataTransfer.files.length) {
      inp.files = e.dataTransfer.files;
      // Optional auto-submit
      var form = dz.closest('form');
      if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
    }
  });
})();
