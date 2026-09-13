import './DataTable.css'

// Reusable list display for every future data screen (cases, members,
// subscriptions, ...). Always handles the three required states explicitly —
// Loading / Error / Empty — instead of leaving that to each caller.
export default function DataTable({ columns, rows, loading, error, emptyMessage = 'אין נתונים להצגה.', onRowClick }) {
  if (loading) {
    return <div className="data-table-state">טוען…</div>
  }

  if (error) {
    return <div className="data-table-state data-table-state-error">{error}</div>
  }

  if (!rows || rows.length === 0) {
    return <div className="data-table-state">{emptyMessage}</div>
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column.key}>{column.label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr
            key={row.id ?? index}
            className={onRowClick ? 'data-table-row-clickable' : undefined}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
          >
            {columns.map((column) => (
              <td key={column.key}>{column.render ? column.render(row) : row[column.key]}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
