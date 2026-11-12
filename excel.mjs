import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.dirname(fileURLToPath(import.meta.url));
const workbook = Workbook.create();
const tables = [
  ['Comparaison','results/synthese.csv'],['Capital','results/capital.csv'],
  ['Allocations','results/poids.csv'],['Transactions','results/transactions.csv'],
  ['Cours USD','data/prices.csv']
];
for (const [name,file] of tables) {
  const sheet = workbook.worksheets.add(name);
  const csv = await fs.readFile(path.join(root,file),'utf8');
  const rows = csv.trim().split(/\r?\n/).map(line=>line.split(',').map(v=>Number.isFinite(Number(v))?Number(v):v));
  const end = String.fromCharCode(64+rows[0].length);
  sheet.getRange('A1:'+end+rows.length).values = rows;
  const header = sheet.getRange('A1:'+end+'1');
  header.format.fill='#16374B';
  header.format.font.color='#FFFFFF';
  header.format.font.bold=true;
  sheet.getRange('A:'+end).format.columnWidth=23;
  sheet.freezePanes.freezeRows(1);
  if(name==='Comparaison'){
    sheet.getRange('B2:F6').setNumberFormat('0.00%');
    sheet.getRange('D2:D6').setNumberFormat('0.00');
  } else {
    const start = ['Allocations','Transactions'].includes(name)?'C':'B';
    sheet.getRange(start+'2:'+end+rows.length).setNumberFormat(start==='C'?'0.00%':'0.00');
  }
}
await (await SpreadsheetFile.exportXlsx(workbook)).save(path.join(root,'results/allocation.xlsx'));
