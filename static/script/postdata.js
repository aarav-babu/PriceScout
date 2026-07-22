// Live preview + completion progress for the valuation forms.
(function () {
  var form = document.querySelector('.form-main form');
  if (!form) return;

  var titleEl = document.querySelector('[data-preview="title"]');
  var subEl = document.querySelector('[data-preview="sub"]');
  var fillEl = document.querySelector('[data-progress="fill"]');
  var countEl = document.querySelector('[data-progress="count"]');
  var totalEl = document.querySelector('[data-progress="total"]');

  var defaultTitle = titleEl ? titleEl.textContent.trim() : '';

  var brand = form.querySelector('[name="brand"]');
  var model = form.querySelector('[name="name-model"], [name="model-name"], [name="model"]');
  var year = form.querySelector('[name="model-year"]');

  var fields = Array.prototype.slice.call(
    form.querySelectorAll('input[required], select[required], textarea[required]')
  );
  var total = fields.length;
  if (totalEl) totalEl.textContent = total;

  function filledCount() {
    var n = 0;
    fields.forEach(function (f) {
      if (f.value && String(f.value).trim() !== '') n++;
    });
    return n;
  }

  function update() {
    // Live title from year + brand + model
    var parts = [];
    if (year && year.value.trim()) parts.push(year.value.trim());
    if (brand && brand.value.trim()) parts.push(brand.value.trim());
    if (model && model.value.trim()) parts.push(model.value.trim());
    var title = parts.join(' ').trim();

    if (titleEl) titleEl.textContent = title || defaultTitle;

    var count = filledCount();
    var pct = total ? Math.round((count / total) * 100) : 0;
    if (fillEl) fillEl.style.width = pct + '%';
    if (countEl) countEl.textContent = count;
    if (subEl) {
      subEl.textContent = count >= total
        ? 'All set - ready for an estimate'
        : (total - count) + ' detail' + ((total - count) === 1 ? '' : 's') + ' to go';
    }
  }

  form.addEventListener('input', update);
  form.addEventListener('change', update);
  update();
})();
