import type { Turn } from "./types";

export default function ResultTable({
  table,
}: {
  table: NonNullable<Turn["result_table"]>;
}) {
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label="Computed result table"
    >
      <table>
        <caption>
          Showing {table.rows.length} of {table.total_rows} rows and{" "}
          {table.columns.length} of {table.total_columns} columns
        </caption>
        <thead>
          <tr>
            <th scope="col">Index</th>
            {table.columns.map((c, i) => (
              <th scope="col" key={i}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, i) => (
            <tr key={i}>
              <th scope="row">{table.index[i]}</th>
              {row.map((cell, j) => (
                <td key={j}>{cell === null ? "Missing" : String(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
