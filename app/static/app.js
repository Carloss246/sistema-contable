function addMovimientoRow() {
  const tbody = document.getElementById('movimientosBody');
  if (!tbody) return;

  const template = tbody.querySelector('.movimiento-row');
  if (!template) return;

  const clone = template.cloneNode(true);
  clone.querySelectorAll('input').forEach(input => input.value = '');
  clone.querySelectorAll('select').forEach(select => select.selectedIndex = 0);
  tbody.appendChild(clone);
}

function removeMovimientoRow(button) {
  const tbody = document.getElementById('movimientosBody');
  if (!tbody) return;
  const row = button.closest('tr');
  if (!row) return;
  if (tbody.querySelectorAll('.movimiento-row').length <= 2) {
    alert('Debes mantener al menos dos movimientos.');
    return;
  }
  row.remove();
}
