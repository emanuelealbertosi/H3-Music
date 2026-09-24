from pathlib import Path
p=Path(r'F:\H3-Music\static\app.js');s=p.read_text(encoding='utf-8')
old="$('#abc').value=$('#abc').value.replace(/\"[^\"\\r\\n]*\"/g,'');"
new="$('#abc').value=$('#abc').value.split('\\n').map(line=>/^[A-Za-z]:|^%/.test(line)?line:line.replace(/\"[^\"\\r\\n]*\"/g,'')).join('\\n');"
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf-8')
