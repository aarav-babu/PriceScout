// Pop-out detail view for saved valuations.
(function () {
  var modal = document.getElementById('detailModal');
  if (!modal) return;

  var dmThumb = document.getElementById('dmThumb');
  var dmBadge = document.getElementById('dmBadge');
  var dmTitle = document.getElementById('dmTitle');
  var dmPrice = document.getElementById('dmPrice');
  var dmBody = document.getElementById('dmBody');
  var dmDesc = document.getElementById('dmDesc');

  function openModal(card) {
    var img = card.querySelector('.post-thumb img');
    var badge = card.querySelector('.post-badge');
    var title = card.querySelector('.post-title');
    var price = card.querySelector('.post-price');
    var desc = card.querySelector('.post-desc');
    var detail = card.querySelector('.post-detail-data');

    dmThumb.src = img ? img.getAttribute('src') : '';
    dmThumb.alt = badge ? badge.textContent : '';
    dmBadge.textContent = badge ? badge.textContent : '';
    dmTitle.textContent = title ? title.textContent : '';
    dmPrice.textContent = price ? price.textContent : '';
    dmBody.innerHTML = detail ? detail.innerHTML : '';
    dmDesc.textContent = desc ? desc.textContent : '';

    modal.hidden = false;
    // next frame so the transition runs
    requestAnimationFrame(function () { modal.classList.add('open'); });
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.classList.remove('open');
    document.body.style.overflow = '';
    setTimeout(function () { modal.hidden = true; }, 200);
  }

  document.querySelectorAll('.post-card').forEach(function (card) {
    card.addEventListener('click', function () { openModal(card); });
    card.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openModal(card);
      }
    });
  });

  modal.querySelectorAll('[data-close]').forEach(function (el) {
    el.addEventListener('click', closeModal);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !modal.hidden) closeModal();
  });
})();
