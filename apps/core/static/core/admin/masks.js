/* Máscaras dos campos do painel (JS puro).
   Uso: <input data-mask="money|area|cep|phone|uf|cpf_cnpj|creci"> */
(function () {
  function digits(v) { return v.replace(/\D/g, ''); }

  function group(intPart) { return intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.'); }

  function decimal(v, places) {
    var neg = v.indexOf('-') === 0 ? '-' : '';
    var raw = v.replace(/[^\d,]/g, '');
    var i = raw.indexOf(',');
    var intPart = i === -1 ? raw : raw.slice(0, i);
    var frac = i === -1 ? null : raw.slice(i + 1).replace(/,/g, '').slice(0, places);
    intPart = group(intPart.replace(/^0+(?=\d)/, ''));
    return neg + intPart + (frac === null ? '' : ',' + frac);
  }

  // Valor vindo do servidor ("980000,00" ou "980000.00") -> "980.000,00"
  function fromServer(v, places) {
    v = v.trim();
    if (!v) return '';
    if (v.indexOf(',') === -1 && /^\d+\.\d+$/.test(v)) v = v.replace('.', ',');
    var out = decimal(v, places);
    if (!out) return '';
    if (out.indexOf(',') === -1) return out + ',' + '0'.repeat(places);
    return out + '0'.repeat(places - (out.length - out.indexOf(',') - 1));
  }

  function wrap(prefix, suffix, fn) {
    return function (v) {
      var d = fn(v.replace('R$', '').replace('m²', ''));
      return d ? prefix + d + suffix : '';
    };
  }

  var masks = {
    money: {
      live: wrap('R$ ', '', function (v) { return decimal(v, 2); }),
      blur: wrap('R$ ', '', function (v) { return fromServer(v, 2); })
    },
    area: {
      live: wrap('', ' m²', function (v) { return decimal(v, 2); }),
      blur: wrap('', ' m²', function (v) { return fromServer(v, 2); })
    },
    cep: {
      live: function (v) {
        var d = digits(v).slice(0, 8);
        return d.length > 5 ? d.slice(0, 5) + '-' + d.slice(5) : d;
      }
    },
    phone: {
      live: function (v) {
        var d = digits(v).slice(0, 11);
        if (d.length > 10) return '(' + d.slice(0, 2) + ') ' + d.slice(2, 7) + '-' + d.slice(7);
        if (d.length > 6) return '(' + d.slice(0, 2) + ') ' + d.slice(2, 6) + '-' + d.slice(6);
        if (d.length > 2) return '(' + d.slice(0, 2) + ') ' + d.slice(2);
        return d ? '(' + d : '';
      }
    },
    uf: { live: function (v) { return v.replace(/[^a-zA-Z]/g, '').toUpperCase().slice(0, 2); } },
    cpf_cnpj: {
      live: function (v) {
        var d = digits(v).slice(0, 14);
        if (d.length <= 11) {
          return d.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2')
            .replace(/(\d{3})(\d{1,2})$/, '$1-$2');
        }
        return d.replace(/^(\d{2})(\d)/, '$1.$2').replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
          .replace(/\.(\d{3})(\d)/, '.$1/$2').replace(/(\d{4})(\d)/, '$1-$2');
      }
    },
    creci: {
      live: function (v) { return v.toUpperCase().replace(/[^A-Z0-9\-\/ ]/g, '').slice(0, 20); }
    }
  };

  function attach(input) {
    var m = masks[input.dataset.mask];
    if (!m || input.dataset.maskReady) return;
    input.dataset.maskReady = '1';
    var apply = function (fn) { input.value = fn(input.value); };
    if (input.value) apply(m.blur || m.live);
    input.addEventListener('input', function () { apply(m.live); });
    if (m.blur) input.addEventListener('blur', function () { apply(m.blur); });
  }

  function init() { document.querySelectorAll('input[data-mask]').forEach(attach); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
  // linhas de inline adicionadas dinamicamente
  new MutationObserver(init).observe(document.documentElement, { childList: true, subtree: true });
})();
