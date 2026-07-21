# Fontes — proveniência das obras de domínio público

Toda passagem que entra num corpus deste estudo vem de uma destas obras, e carrega no
próprio registro a obra, o autor, o tradutor e o ano. Um corpus publicado sem endereço por
item é uma citação que ninguém pode conferir.

Baixadas em 2026-07-21 por [`harness/fetch_sources.py`](../harness/fetch_sources.py), que
**verifica o tradutor no próprio texto** e aborta se o nome da lista aprovada não aparecer.
Cada arquivo em `sources/` guarda no front-matter o `sha256` do download original.

## Leokadius — estoico

| Obra | Autor | Tradutor | Ano | # | Corpo |
|---|---|---|---|---|---|
| Thoughts of Marcus Aurelius Antoninus | Marco Aurélio | George Long | 1862 | 15877 | 421 KB |
| A Selection from the Discourses of Epictetus with the Encheiridion | Epicteto | George Long | 1877 | 10661 | 323 KB |
| Minor Dialogues, com o Diálogo sobre a Clemência | Sêneca | Aubrey Stewart | 1889 | 64576 | 818 KB |
| The Lives and Opinions of Eminent Philosophers | Diógenes Laércio | Charles Duke Yonge | 1853 | 57342 | 1.095 KB |

Diógenes Laércio entra **apenas pelo Livro VII** (Zenão e os estoicos): o handoff admite
Zenão só por essa via, e o restante da obra cobre escolas que não são desta persona. O
recorte é feito no construtor de corpus, não no download, para que o arquivo baixado
continue idêntico à fonte.

**Sêneca — substituição aprovada.** A tradução da lista original (Gummere, *Moral Letters*)
não existe no Project Gutenberg; está no Wikisource, edição Loeb 1917–25. O Arquiteto
aprovou em 2026-07-21 a substituição por **Aubrey Stewart** (*Minor Dialogues*, 1889), que
tem tradutor registrado, verificável no próprio texto, e traz *De Tranquillitate Animi* e
*De Ira* — respectivamente a fonte do movimento `prosoche`, que sem ela fechava em 11 de 46,
e o tema "ira" previsto para a bateria de Leokadius.

## Shadowclock — existencialista ateu

| Obra | Autor | Tradutor | Ano | # | Corpo |
|---|---|---|---|---|---|
| Thus Spake Zarathustra | Nietzsche | Thomas Common | 1909 | 1998 | 638 KB |
| Beyond Good and Evil | Nietzsche | Helen Zimmern | 1907 | 4363 | 380 KB |
| The Joyful Wisdom | Nietzsche | Thomas Common | 1910 | 52881 | 530 KB |
| Notes from the Underground | Dostoiévski | Constance Garnett | 1918 | 600 | 238 KB |
| Essays and Dialogues | Leopardi | Charles Edwardes | 1882 | 52356 | 435 KB |
| The Ego and His Own | Max Stirner | Steven T. Byington | 1907 | 34580 | 847 KB |
| The Essence of Christianity | Feuerbach | Marian Evans (George Eliot) | 1854 | 47025 | 870 KB |

Feuerbach aparece no catálogo sob "George Eliot", que é o pseudônimo de Marian Evans — é a
tradução da lista aprovada.

## Substituições, com motivo

**Meditations #2680 → Thoughts of Marcus Aurelius Antoninus #15877.** A edição #2680 é a
mais conhecida, mas **não atribui tradutor** nem no texto nem no catálogo. Como este estudo
publica corpora com atribuição por item — e recusou fontes de terceiros exatamente por
faltar tradutor e ano —, usá-la seria aplicar dois pesos. A #15877 é a mesma obra
**atribuída a George Long**, que é o tradutor da lista aprovada, e a atribuição foi
confirmada no corpo do arquivo.

## O que foi recusado, e por quê

**Traduções de Sêneca para o espanhol** (coleção local, do portal Domínio Público do MEC).
Recusadas — não por serem espanholas em si, mas por três razões, em ordem de peso:

1. **Assimetria entre braços.** Shadowclock ficaria integralmente em inglês e Leokadius
   parte em espanhol. Isso é diferença sistemática no *input de treino* entre os dois
   braços, e a receita casada existe justamente para impedir que a persona se confunda com
   a dose. Com o grounding em idiomas diferentes, um contraste de registro entre as duas
   personas deixaria de ser interpretável — e "é a receita, não a persona" é hipótese rival
   nomeada no pré-registro.
2. **Interferência espanhol→português.** O professor lê as âncoras e gera em português. A
   proximidade entre as duas línguas, que parece vantagem, é o risco: léxico e sintaxe
   espanhóis vazam para a geração com muito mais facilidade do que a partir do inglês — e o
   que vaza para a geração acaba nos pesos.
3. **Proveniência.** Nenhum dos arquivos registra tradutor ou ano; dois trazem
   `Author: clark kent` nos metadados. Sêneca ser domínio público não torna DP qualquer
   tradução dele. Além disso, vários são digitalizações sem texto extraível.

O caminho honesto para incluir outro idioma seria **simétrico**: as duas personas com a
mesma mistura de línguas.

**Sartre e Camus** não entram como texto em lugar algum — nem corpus, nem prompt, nem
preâmbulo, nem bateria. Faleceram em 1980 e 1960; as obras entram em domínio público em
2051 e 2031. São nomeados como influência de Shadowclock e nunca excertados; as ideias
aparecem em texto original escrito para este estudo. A regra está no núcleo selado, em
`influencias_nomeadas_nao_citadas`, e é verificada por teste.
