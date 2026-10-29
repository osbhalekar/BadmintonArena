(function () {
  function el(id) { return document.getElementById(id); }

  function show(which) {
    ['payLoading', 'payGateway', 'payFailed'].forEach(function (id) {
      el(id).classList.toggle('d-none', id !== which);
    });
  }

  // Show the spinner for a moment, like a real gateway
  setTimeout(function () { show('payGateway'); }, 1500);

  el('failBtn').addEventListener('click', function () { show('payFailed'); });
  el('retryBtn').addEventListener('click', function () { show('payGateway'); });
})();