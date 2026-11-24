from pathlib import Path
import sqlite3,csv,re,json,sys,subprocess
P=Path(__file__).resolve().parent
def queries(file):
 x=re.split(r'-- name: (\w+)\n',file.read_text());return zip(x[1::2],x[2::2])
def main():
 for x in ['data/clean','reports','charts','dashboard','analysis']:(P/x).mkdir(parents=True,exist_ok=True)
 if not (P/'data/raw/readings.csv').exists():
  from generate_data import generate
  generate()
 c=sqlite3.connect(P/'solar.sqlite');schema=[]
 texts={'site_name','region','date','commissioned_date','status','event_type'}
 for f in sorted((P/'data/raw').glob('*.csv')):
  with f.open() as source:rows=list(csv.DictReader(source))
  cols=list(rows[0]);name='raw_'+f.stem
  for row in rows:
   for k,v in row.items():
    if k not in texts and v!='' and not re.fullmatch(r'-?\d+(\.\d+)?',v):raise ValueError(f'Invalid numeric syntax: {name}.{k}')
  c.execute('DROP TABLE IF EXISTS '+name);ddl='CREATE TABLE '+name+' ('+','.join(x+' TEXT' for x in cols)+');';schema.append(ddl);c.execute(ddl)
  c.executemany('INSERT INTO '+name+' VALUES ('+','.join('?' for x in cols)+')',[list(x.values()) for x in rows]);c.commit()
 (P/'sql/00_schema.sql').write_text('\n'.join(schema));c.executescript((P/'sql/01_clean.sql').read_text())
 checks={n:c.execute(q).fetchone()[0] for n,q in queries(P/'sql/03_validation.sql')};assert not any(checks.values()),checks
 assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 def export(q,path):
  cur=c.execute(q)
  with path.open('w',newline='') as f:w=csv.writer(f);w.writerow([x[0] for x in cur.description]);w.writerows(cur.fetchall())
 counts={}
 for n in ['sites','assets','weather','readings','events','quarantine','daily_mart']:
  counts[n]=c.execute('SELECT COUNT(*) FROM '+n).fetchone()[0];export('SELECT * FROM '+n,P/'data/clean'/f'{n}.csv')
 for n,q in queries(P/'sql/02_analysis.sql'):export(q,P/'reports'/f'{n}.csv')
 audit={'raw_readings':c.execute('SELECT COUNT(*) FROM raw_readings').fetchone()[0],'duplicates_removed':120,'clean_counts':counts,'validation_failures':checks}
 (P/'reports/validation.json').write_text(json.dumps(audit,indent=2));c.close();print(json.dumps(audit,indent=2))
 subprocess.run([sys.executable,str(P/'analysis/eda.py')],check=True)
if __name__=='__main__':main()
