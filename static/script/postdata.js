// Multi-step wizard for the valuation forms. Each <fieldset.form-section> is a
// step; the stepper is built from the section legends so it works across all
// three forms without per-page config.
(function () {
  var wizard = document.querySelector('.wizard');
  if (!wizard) return;

  var form = wizard.querySelector('form');
  var steps = Array.prototype.slice.call(form.querySelectorAll('.form-section'));
  if (!steps.length) return;

  var stepperEl = wizard.querySelector('.stepper');
  var progressFill = wizard.querySelector('.wizard-progress span');
  var prevBtn = wizard.querySelector('[data-prev]');
  var nextBtn = wizard.querySelector('[data-next]');
  var submitBtn = wizard.querySelector('[data-submit]');
  var currentEl = wizard.querySelector('[data-current]');
  var totalEl = wizard.querySelector('[data-steps]');

  var current = 0;
  var total = steps.length;
  if (totalEl) totalEl.textContent = total;

  // Build the stepper from each section's legend text.
  steps.forEach(function (section, i) {
    var legend = section.querySelector('legend');
    var name = legend ? legend.textContent.trim() : 'Step ' + (i + 1);
    var li = document.createElement('li');
    li.className = 'step';
    li.innerHTML = '<span class="step-dot"></span><span class="step-label"></span>';
    li.querySelector('.step-label').textContent = name;
    li.addEventListener('click', function () { goTo(i); });
    stepperEl.appendChild(li);
  });

  var stepEls = Array.prototype.slice.call(stepperEl.children);

  function validateStep(i) {
    var fields = steps[i].querySelectorAll('input, select, textarea');
    for (var k = 0; k < fields.length; k++) {
      if (!fields[k].checkValidity()) {
        fields[k].reportValidity();
        return false;
      }
    }
    return true;
  }

  function render(focus) {
    steps.forEach(function (s, i) { s.classList.toggle('is-active', i === current); });
    stepEls.forEach(function (li, i) {
      li.classList.toggle('is-active', i === current);
      li.classList.toggle('is-done', i < current);
    });

    var last = current === total - 1;
    if (prevBtn) prevBtn.hidden = current === 0;
    if (nextBtn) nextBtn.hidden = last;
    if (submitBtn) submitBtn.hidden = !last;
    if (currentEl) currentEl.textContent = current + 1;
    if (progressFill) progressFill.style.width = (((current + 1) / total) * 100) + '%';

    if (focus) {
      var f = steps[current].querySelector('input, select, textarea');
      if (f) { try { f.focus({ preventScroll: true }); } catch (e) { f.focus(); } }
    }
  }

  function goNext() {
    if (!validateStep(current)) return;
    if (current < total - 1) { current++; render(true); }
  }

  function goPrev() {
    if (current > 0) { current--; render(true); }
  }

  function goTo(target) {
    if (target === current) return;
    if (target < current) { current = target; render(true); return; }
    // Moving forward: every step in between must be valid.
    for (var i = current; i < target; i++) {
      if (!validateStep(i)) { current = i; render(true); return; }
    }
    current = target;
    render(true);
  }

  if (nextBtn) nextBtn.addEventListener('click', goNext);
  if (prevBtn) prevBtn.addEventListener('click', goPrev);

  // Enter should advance the wizard, not submit early (textarea keeps newlines).
  form.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
      if (current < total - 1) { e.preventDefault(); goNext(); }
    }
  });

  render(false);
})();
