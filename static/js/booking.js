
(function () {
  var cfg = JSON.parse(document.getElementById('book-config').textContent);

  var DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                'August', 'September', 'October', 'November', 'December'];

  var RULES = {
    weekly: 'Pick any 2 days in the same week.',
    monthly: 'Pick 2 different weekdays. We add 4 weeks of each (8 days).',
    custom: 'Pick any 8 days in the same month.'
  };

  function el(id) { return document.getElementById(id); }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function iso(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function parse(s) { var p = s.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function addDays(d, n) { return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n); }
  function toMin(t) { var p = t.split(':'); return +p[0] * 60 + +p[1]; }
  function money(n) { return '₹' + n.toLocaleString('en-IN'); }
  function fmtTime(min) {
    var h = Math.floor(min / 60), m = min % 60;
    return (h % 12 || 12) + ':' + pad(m) + ' ' + (h >= 12 ? 'PM' : 'AM');
  }
  function fmtDate(d) {
    return DAYS[d.getDay()] + ', ' + d.getDate() + ' ' + MONTHS[d.getMonth()].slice(0, 3) + ' ' + d.getFullYear();
  }
  function weekStart(d) { return iso(addDays(d, -d.getDay())); }

  var today = parse(cfg.today);
  var view = new Date(today.getFullYear(), today.getMonth(), 1);
  var state = { players: 2, startHour: 18, picked: [] };
  var need = cfg.plan_type === 'monthly' ? 2 : cfg.days_allowed;

  /* start time options */
  var startSelect = el('startSelect');
  var lastStart = Math.floor((cfg.close_hour * 60 - cfg.duration_minutes) / 60);
  if (state.startHour > lastStart) state.startHour = lastStart;
  for (var h = cfg.open_hour; h <= lastStart; h++) {
    var opt = document.createElement('option');
    opt.value = h;
    opt.textContent = fmtTime(h * 60);
    if (h === state.startHour) opt.selected = true;
    startSelect.appendChild(opt);
  }

  /* helpers */
  function isBooked(key) {
    var s = state.startHour * 60, e = s + cfg.duration_minutes;
    return cfg.booked.some(function (b) {
      return b.date === key && s < toMin(b.end) && e > toMin(b.start);
    });
  }

  // All days covered by the picks (Standard adds 4 weeks of each pick)
  function derived() {
    var out = {};
    var weeks = cfg.plan_type === 'monthly' ? 4 : 1;
    state.picked.forEach(function (p) {
      var d = parse(p);
      for (var i = 0; i < weeks; i++) out[iso(addDays(d, 7 * i))] = true;
    });
    return Object.keys(out).sort();
  }

  function notify(msg) { el('notice').textContent = msg; }

  /* picking a day */
  function onPick(key) {
    var at = state.picked.indexOf(key);
    if (at > -1) { state.picked.splice(at, 1); return render(); }

    var d = parse(key);
    if (cfg.plan_type === 'weekly') {
      if (state.picked.length >= need) return notify('This plan allows only ' + need + ' days.');
      if (state.picked.length && weekStart(d) !== weekStart(parse(state.picked[0]))) {
        return notify('Both days must be in the same week.');
      }
    } else if (cfg.plan_type === 'monthly') {
      if (state.picked.length >= 2) return notify('Pick only 2 weekdays. Click a selected day to change it.');
      var sameWeekday = state.picked.some(function (p) { return parse(p).getDay() === d.getDay(); });
      if (sameWeekday) return notify('Choose two different weekdays.');
    } else {
      if (state.picked.length >= need) return notify('You can choose only ' + need + ' days.');
      if (state.picked.length) {
        var f = parse(state.picked[0]);
        if (f.getMonth() !== d.getMonth() || f.getFullYear() !== d.getFullYear()) {
          return notify('All days must be in the same month.');
        }
      }
    }
    state.picked.push(key);
    state.picked.sort();
    render();
  }

  /* calendar */
  function renderCalendar() {
    var y = view.getFullYear(), m = view.getMonth();
    el('calTitle').textContent = MONTHS[m] + ' ' + y;

    var grid = el('calGrid');
    grid.innerHTML = '';
    var chosen = {};
    derived().forEach(function (k) { chosen[k] = true; });

    var lead = new Date(y, m, 1).getDay();
    for (var i = 0; i < lead; i++) grid.appendChild(document.createElement('div'));

    var total = new Date(y, m + 1, 0).getDate();
    for (var day = 1; day <= total; day++) {
      var date = new Date(y, m, day);
      var key = iso(date);
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'tile';
      btn.dataset.date = key;
      var note = '';

      if (chosen[key]) {
        btn.classList.add('tile-selected');
        if (cfg.holidays[key]) { btn.classList.add('tile-warn'); note = 'Shifts'; }
        else if (isBooked(key)) { btn.classList.add('tile-warn'); note = 'Taken'; }
        if (state.picked.indexOf(key) === -1) btn.disabled = true;   // auto-added days
      } else if (date <= today) {
        btn.classList.add('tile-past'); btn.disabled = true;
      } else if (cfg.holidays[key]) {
        btn.classList.add('tile-holiday'); btn.disabled = true; note = cfg.holidays[key];
      } else if (isBooked(key)) {
        btn.classList.add('tile-booked'); btn.disabled = true; note = 'Booked';
      }

      var num = document.createElement('span');
      num.textContent = day;
      btn.appendChild(num);
      if (note) {
        var small = document.createElement('span');
        small.className = 'tile-note';
        small.textContent = note;
        btn.appendChild(small);
      }
      grid.appendChild(btn);
    }

    var firstMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    var lastMonth = new Date(today.getFullYear(), today.getMonth() + 12, 1);
    el('prevMonth').disabled = view <= firstMonth;
    el('nextMonth').disabled = view >= lastMonth;
  }

  /* summary */
  function renderSummary() {
    var keys = derived();
    var s = state.startHour * 60, e = s + cfg.duration_minutes;
    var list = el('summaryList');
    list.innerHTML = '';

    keys.forEach(function (k) {
      var row = document.createElement('div');
      row.className = 'summary-item';
      var title = document.createElement('div');
      title.textContent = fmtDate(parse(k));
      if (cfg.holidays[k]) {
        var b1 = document.createElement('span');
        b1.className = 'badge text-bg-warning ms-2';
        b1.textContent = 'Holiday: moves to next day';
        title.appendChild(b1);
      } else if (isBooked(k)) {
        var b2 = document.createElement('span');
        b2.className = 'badge text-bg-danger ms-2';
        b2.textContent = 'Taken: pick another day';
        title.appendChild(b2);
      }
      var time = document.createElement('small');
      time.className = 'text-secondary';
      time.textContent = fmtTime(s) + ' - ' + fmtTime(e);
      row.appendChild(title);
      row.appendChild(time);
      list.appendChild(row);
    });

    var gross = cfg.price_per_person * state.players * keys.length;
    var disc = Math.floor(gross * cfg.discount_percent / 100);
    el('sumDays').textContent = keys.length;
    el('sumGross').textContent = money(gross);
    el('sumDisc').textContent = '- ' + money(disc);
    el('sumTotal').textContent = money(gross - disc);
    el('endText').textContent = fmtTime(e);

    var ready = state.picked.length === need;
    el('hint').textContent = ready ? '' : 'Pick ' + (need - state.picked.length) + ' more day(s).';
    el('confirmBtn').disabled = !ready;

    el('fPicked').value = state.picked.join(',');
    el('fStart').value = pad(state.startHour) + ':00';
    el('fPlayers').value = state.players;
  }

  function render() {
    notify('');
    renderCalendar();
    renderSummary();
  }

  /* events */
  el('calGrid').addEventListener('click', function (ev) {
    var btn = ev.target.closest('.tile');
    if (btn && !btn.disabled) onPick(btn.dataset.date);
  });

  el('prevMonth').addEventListener('click', function () {
    view = new Date(view.getFullYear(), view.getMonth() - 1, 1);
    renderCalendar();
  });

  el('nextMonth').addEventListener('click', function () {
    view = new Date(view.getFullYear(), view.getMonth() + 1, 1);
    renderCalendar();
  });

  startSelect.addEventListener('change', function () {
    state.startHour = +startSelect.value;
    render();
  });

  document.querySelectorAll('.choice-card').forEach(function (card) {
    card.addEventListener('click', function () {
      document.querySelectorAll('.choice-card').forEach(function (c) { c.classList.remove('active'); });
      card.classList.add('active');
      state.players = +card.dataset.players;
      renderSummary();
    });
  });

  el('rules').textContent = RULES[cfg.plan_type] || '';
  render();
})();