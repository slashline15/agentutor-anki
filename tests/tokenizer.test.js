/* Testes do templates/tokenizer.js (rodar: node --test tests/)
   O teste mais importante: o modo padrão ("auto") produz saída BYTE-IDÊNTICA
   ao tokenizer antigo que estava duplicado nos 5 HTML — cards antigos não
   podem mudar de aparência. */
const { test } = require('node:test');
const assert = require('node:assert');
const TermHl = require('../templates/tokenizer.js');

// ---- reimplementação LITERAL do tokenizador antigo (copiada dos HTML) ------
const PY_KW = ['False','None','True','and','as','assert','async','await','break','case','catch','class','const','continue','def','default','del','delete','do','elif','else','except','export','extends','false','finally','for','from','function','global','if','import','in','instanceof','is','lambda','let','new','nonlocal','not','null','of','or','pass','raise','return','static','super','switch','this','throw','true','try','typeof','undefined','var','void','while','with','yield'];
const PY_BI = ['abs','alert','all','any','Array','bool','Boolean','console','dict','document','enumerate','filter','float','format','frozenset','input','int','isNaN','JSON','len','list','map','Math','max','min','Number','Object','open','parseFloat','parseInt','print','prompt','range','repr','reversed','round','set','sorted','str','String','sum','tuple','type','window','zip'];
function esc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function buildRe(){
  return new RegExp(
    '(#[^\\n]*)|' +
    '("""[\\s\\S]*?"""|\'\'\'[\\s\\S]*?\'\'\')|' +
    '("(?:\\\\.|[^"\\\\])*"|\'(?:\\\\.|[^\'\\\\])*\')|' +
    '\\b(\\d+\\.?\\d*)\\b|' +
    '(@[A-Za-z_]\\w*)|' +
    '\\b(' + PY_KW.join('|') + ')\\b|' +
    '\\b(' + PY_BI.join('|') + ')\\b', 'g');
}
function tokenizeAntigo(code){
  var re = buildRe(), out = '', last = 0, m;
  while ((m = re.exec(code)) !== null){
    out += esc(code.slice(last, m.index));
    if (m[1])      out += '<span class="tok-comment">'   + esc(m[1]) + '</span>';
    else if (m[2]) out += '<span class="tok-string">'    + esc(m[2]) + '</span>';
    else if (m[3]) out += '<span class="tok-string">'    + esc(m[3]) + '</span>';
    else if (m[4]) out += '<span class="tok-number">'    + esc(m[4]) + '</span>';
    else if (m[5]) out += '<span class="tok-decorator">' + esc(m[5]) + '</span>';
    else if (m[6]) out += '<span class="tok-keyword">'   + esc(m[6]) + '</span>';
    else if (m[7]) out += '<span class="tok-builtin">'   + esc(m[7]) + '</span>';
    last = re.lastIndex;
  }
  return out + esc(code.slice(last));
}

const AMOSTRAS = [
  'def soma(a, b):\n    return a + b  # comenta',
  'x = "texto com <tag> & aspas \\" ok"\nprint(len(x))',
  "'''doc\nstring'''\nfor i in range(10):\n    print(i * 2.5)",
  '@decorator\nclass Foo:\n    pass',
  'const f = (x) => { return Math.max(x, 0); } // js tambem',
  'valores = [1, 2, 3]\ntotal = sum(valores)',
];

test('modo padrão é byte-idêntico ao tokenizer antigo (cards antigos intactos)', () => {
  for (const code of AMOSTRAS) {
    assert.strictEqual(TermHl.tokenize(code, 'auto'), tokenizeAntigo(code));
    assert.strictEqual(TermHl.tokenize(code), tokenizeAntigo(code));       // sem lang
    assert.strictEqual(TermHl.tokenize(code, 'python'), tokenizeAntigo(code));
    assert.strictEqual(TermHl.tokenize(code, 'inexistente'), tokenizeAntigo(code));
  }
});

test('bash: keywords, builtins, variáveis e strings', () => {
  // variável DENTRO de aspas vira string inteira (precedência correta);
  // fora de aspas ganha o span próprio
  const out = TermHl.tokenize('if [ -f $ARQ ]; then\n  echo "ok ${NOME}"\n  cp ${ORIGEM} /tmp\nfi # fim', 'bash');
  assert.match(out, /<span class="tok-keyword">if<\/span>/);
  assert.match(out, /<span class="tok-keyword">then<\/span>/);
  assert.match(out, /<span class="tok-keyword">fi<\/span>/);
  assert.match(out, /<span class="tok-builtin">echo<\/span>/);
  assert.match(out, /<span class="tok-decorator">\$ARQ<\/span>/);
  assert.match(out, /<span class="tok-decorator">\$\{ORIGEM\}<\/span>/);
  assert.match(out, /<span class="tok-string">"ok \$\{NOME\}"<\/span>/);
  assert.match(out, /<span class="tok-comment"># fim<\/span>/);
});

test('bash: "do"/"done" são keywords em bash (no python-mode "do" já era)', () => {
  const out = TermHl.tokenize('for x in a b; do echo $x; done', 'bash');
  assert.match(out, /<span class="tok-keyword">for<\/span>/);
  assert.match(out, /<span class="tok-keyword">done<\/span>/);
});

test('powershell: cmdlets Verbo-Substantivo, operadores, variáveis', () => {
  const out = TermHl.tokenize(
    'param($Nome)\nif ($x -eq 5) { Get-ChildItem -Path $env:TEMP | Where-Object Name -like "*.log" }',
    'powershell');
  assert.match(out, /<span class="tok-keyword">param<\/span>/);
  assert.match(out, /<span class="tok-keyword">-eq<\/span>/);
  assert.match(out, /<span class="tok-builtin">Get-ChildItem<\/span>/);
  assert.match(out, /<span class="tok-builtin">Where-Object<\/span>/);
  assert.match(out, /<span class="tok-decorator">\$Nome<\/span>/);
  assert.match(out, /<span class="tok-keyword">-like<\/span>/);
});

test('powershell: comentário de bloco <# #> e aspas com crase', () => {
  const out = TermHl.tokenize('<# bloco\nde comentario #>\n$s = "com `"escape`""', 'powershell');
  assert.match(out, /tok-comment/);
  assert.match(out, /tok-string/);
});

test('apelidos de linguagem mapeiam certo (sh->bash, ps1->powershell)', () => {
  assert.strictEqual(TermHl.tokenize('echo hi', 'sh'), TermHl.tokenize('echo hi', 'bash'));
  assert.strictEqual(TermHl.tokenize('$a -eq 1', 'ps1'), TermHl.tokenize('$a -eq 1', 'powershell'));
});

test('HTML é escapado em todas as linguagens', () => {
  for (const lang of ['auto', 'bash', 'powershell']) {
    const out = TermHl.tokenize('a < b && c > "<script>"', lang);
    assert.ok(!out.includes('<script>'), lang + ': nao pode vazar <script>');
    assert.ok(out.includes('&lt;'), lang + ': deve escapar <');
  }
});
