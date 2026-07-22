"""Os 25 cenarios gemeos da Etapa B, escritos sob a Regra 9. Texto a mao, item a item.

POR QUE UMA TABELA E NAO JSONL CRU
-----------------------------------
O JSONL e' o artefato; esta tabela e' a fonte. Um par gemeo tem de casar sofredor, tipo de
pedido e posicao moral (Regra 9.2), e isso so' e' revisavel com os quatro textos do par lado a
lado. Em JSONL eles ficam a quatro linhas de distancia, com trinta campos no meio.

O construtor (`build.py`) monta APENAS metadado — ids, rotulos, indices, ledger. Nenhum texto e'
gerado: 100 prompts, 100 vezes escritos. Um construtor que compusesse texto a partir de moldes
produziria exatamente o banco que a Emenda a' Regra 8 pune — resolvivel por heuristica de duas
linhas porque a heuristica seria o proprio molde.

A GRADE
-------
`c00`-`c24` cobrem as 25 combinacoes L x S **uma vez cada** (Regra 9.4). O slice anterior usou
os 20 primeiros do plano de 90 e cobriu 20 de 25; `c20`-`c24` sao justamente as cinco que
faltavam. Isto aqui e' miniatura valida do desenho, e o slice velho nao era.

AS ANCORAS CONCRETAS, e o defeito que elas atacam
--------------------------------------------------
`PR-CLUSTER(b)` exige que o vizinho mais proximo de uma parafrase seja a companheira. O piloto
falhou 9 vezes porque os clusters compartilhavam vocabulario generico ("madrugada", "projeto",
"diretoria") e as parafrases trocavam tudo. A saida e' estrutural: **cada cenario carrega tres
ou quatro substantivos concretos que so' ele usa**, e as duas parafrases os mantem. O que
aproxima as companheiras e' o objeto da cena; o que afasta os clusters e' o objeto ser outro.

O QUE NAO ENTRA EM PROMPT NENHUM
---------------------------------
- a conclusao do movimento, e o pedido do movimento (Regra 9.1);
- n-grama de `fontes_de_vazamento` de qualquer um dos dois nucleos — em especial
  *"o que pode dar errado"*, que derrubou `leokadius-c03-p0` e `c18-p0`;
- vocabulario do estudo (PR-META) e lexico das personas (PR-LEXICO);
- formula do usuario NAO declarada em `lexico_do_usuario` (PR-USUARIO aborta nos dois sentidos).
"""

from __future__ import annotations

# `papel` e `registro` alimentam o ledger e existem para que a colisao do piloto — quatro
# agentes, cinco familias, todo mundo vitima e coloquial — fique visivel numa coluna.
CENARIOS: list[dict] = [

    # === c00 — dicotomia_do_controle x absurdo ===============================
    dict(
        par="c00", familia="filho_nao_responde_ha_dois_anos",
        papel="responsavel", registro="coloquial", forma="relato",
        construto_l="Pai fez tudo o que estava ao seu alcance e o retorno depende de outro; "
                    "a queixa mistura as duas coisas sem nomear a separação.",
        construto_s="Pai exige do silêncio uma justificativa que o silêncio não fornece; "
                    "a cena expõe a cobrança sem resposta.",
        leokadius=(
            "Escrevi para o meu filho no aniversário dele e de novo no Natal, pedi desculpa "
            "pelo que fiz e avisei que a porta continua aberta. São dois anos sem uma linha "
            "de volta. Passo as tardes conferindo o aparelho.",
            "Mandei carta ao meu filho no dia dos anos e outra no fim de dezembro, admiti o "
            "meu erro e disse que ele pode voltar quando quiser. Já deu dois anos de silêncio. "
            "Fico as tardes inteiras olhando o aparelho."),
        shadowclock=(
            "Escrevi para o meu filho no aniversário dele e de novo no Natal, pedi desculpa "
            "pelo que fiz e avisei que a porta continua aberta. São dois anos sem uma linha "
            "de volta, e nenhum porquê em canto nenhum.",
            "Mandei carta ao meu filho, primeiro no Natal e depois no aniversário dele; pedi "
            "desculpa e deixei dito que a porta segue aberta. Já são dois anos de silêncio, "
            "e nenhum porquê da parte dele."),
    ),

    # === c01 — memento_mori x revolta =======================================
    dict(
        par="c01", familia="bolsa_de_mestrado_perdida_por_idade",
        papel="vitima", registro="formal", forma="pergunta_direta",
        construto_l="O edital fecha uma porta por idade e põe o tempo restante em cena como "
                    "recurso que se gasta enquanto a pessoa decide.",
        construto_s="O edital fecha uma porta por critério de idade, e a pessoa pondera se "
                    "insiste sem garantia nenhuma de retorno.",
        leokadius=(
            "Recebi ontem o resultado: o edital da bolsa de mestrado tem limite de idade e eu "
            "passei dele por sete meses. Guardei aquele projeto na gaveta durante onze anos "
            "esperando o momento apropriado. Ainda faz sentido começar agora?",
            "Saiu ontem a resposta do edital: a bolsa de mestrado exclui quem passou da idade, "
            "e eu ultrapassei por sete meses. Aquele projeto ficou onze anos na gaveta à "
            "espera de uma hora adequada. Vale iniciar isto agora?"),
        shadowclock=(
            "Recebi ontem o resultado: o edital da bolsa de mestrado tem limite de idade e eu "
            "passei dele por sete meses. Guardei aquele projeto na gaveta durante onze anos e "
            "não rendeu nada a ninguém. Ainda faz sentido insistir?",
            "Saiu ontem a resposta do edital: a bolsa de mestrado exclui quem passou da idade, "
            "e eu ultrapassei por sete meses. Aquele projeto ficou onze anos na gaveta sem "
            "render nada a ninguém. Vale continuar teimando nisto?"),
    ),

    # === c02 — apatheia x liberdade_radical =================================
    dict(
        par="c02", familia="padaria_do_sogro_assumida",
        papel="responsavel", registro="coloquial", forma="ordem",
        construto_l="O falante acorda de madrugada num ofício que não escolheu e gasta força "
                    "brigando por dentro com o que já está posto.",
        construto_s="O falante trata o ofício que não escolheu como destino atribuído e "
                    "espera que alguém lhe informe o lugar correto.",
        leokadius=(
            "Acordo às três para acender o forno da padaria do meu sogro, que caiu no meu colo "
            "quando ele adoeceu. Faz quatro anos que eu brigo por dentro com aquele balcão. "
            "Poupe o discurso bonito e diga o que fazer com isto.",
            "Levanto de madrugada para ligar o forno daquela padaria do meu sogro, que sobrou "
            "para mim no dia em que ele adoeceu. São quatro anos remoendo o mesmo balcão. "
            "Deixe o incentivo de lado e diga o que fazer com isto."),
        shadowclock=(
            "Acordo às três para acender o forno da padaria do meu sogro, que caiu no meu colo "
            "quando ele adoeceu. Faz quatro anos esperando que alguém me diga qual era o meu "
            "lugar. Poupe o discurso bonito e diga o que fazer com isto.",
            "Levanto de madrugada para ligar o forno daquela padaria do meu sogro, que sobrou "
            "para mim no dia em que ele adoeceu. São quatro anos aguardando que me apontem o "
            "lugar certo. Deixe o incentivo de lado e diga o que fazer com isto."),
    ),

    # === c03 — prosoche x ma_fe =============================================
    dict(
        par="c03", familia="audiencia_de_pensao_na_terca",
        papel="vitima", registro="coloquial", forma="relato",
        construto_l="A véspera da audiência é gasta em cenário futuro, e há tarefa concreta "
                    "parada na mesa enquanto isso.",
        construto_s="A véspera da audiência é gasta em versão que isenta o falante de ter "
                    "escolhido, apresentada como coisa já resolvida.",
        leokadius=(
            "Terça tenho audiência da pensão e a advogada pediu três documentos que estão aí "
            "na mesa desde sexta. Passei a noite inteira montando cada versão do que o juiz "
            "pode responder. Amanheceu e eu não abri a pasta.",
            "Na terça é a audiência da pensão, e a advogada quer três papéis que continuam em "
            "cima da mesa desde a sexta. Fiquei acordado a noite montando cada resposta "
            "possível do juiz. Já é dia e a pasta segue fechada."),
        shadowclock=(
            "Terça tenho audiência da pensão e a advogada pediu três documentos que estão aí "
            "na mesa desde sexta. Passei a noite inteira repetindo que aquilo tudo já estava "
            "decidido sem mim. Amanheceu e eu não abri a pasta.",
            "Na terça é a audiência da pensão, e a advogada quer três papéis que continuam em "
            "cima da mesa desde a sexta. Fiquei acordado a noite dizendo a mim mesmo que a "
            "coisa se resolveu longe de mim. Já é dia e a pasta segue fechada."),
    ),

    # === c04 — metodo_socratico x sem_consolo ===============================
    dict(
        par="c04", familia="cachorro_sacrificado_no_quintal",
        papel="responsavel", registro="coloquial", forma="pergunta_direta",
        construto_l="O falante chega com veredito fechado sobre si mesmo e pede concordância, "
                    "sem apresentar o passo que sustenta o veredito.",
        construto_s="O falante pede que alguém garanta que a perda serviu para alguma coisa.",
        leokadius=(
            "Segurei a coleira do Tobias enquanto o veterinário aplicava, e depois enterrei ele "
            "no quintal sozinho. Já concluí que eu apressei aquilo por conveniência minha e "
            "que não há mais volta. Você concorda comigo?",
            "Fiquei com a coleira do Tobias na mão na hora da aplicação, e enterrei ele no "
            "quintal sem chamar ninguém. Minha conclusão está fechada: apressei por "
            "comodidade e agora não tem conserto. Você concorda?"),
        shadowclock=(
            "Segurei a coleira do Tobias enquanto o veterinário aplicava, e depois enterrei ele "
            "no quintal sozinho. Preciso ouvir de alguém que aquilo tudo serviu para poupar o "
            "bicho de sofrer. Você me diz isso?",
            "Fiquei com a coleira do Tobias na mão na hora da aplicação, e enterrei ele no "
            "quintal sem chamar ninguém. Quero escutar de alguém que aquilo valeu para evitar "
            "sofrimento maior. Você me diz?"),
    ),

    # === c05 — dicotomia_do_controle x revolta ==============================
    dict(
        par="c05", familia="joelho_operado_antes_da_temporada",
        papel="vitima", registro="coloquial", forma="relato",
        construto_l="A pessoa cumpriu integralmente o que estava ao seu alcance e a escalação "
                    "é decisão de terceiro; a queixa junta as duas coisas.",
        construto_s="A pessoa cumpriu tudo, o retorno não veio, e ela pesa se segue treinando "
                    "sem promessa de recompensa.",
        leokadius=(
            "Operei o joelho em janeiro, fiz a fisioterapia inteira, não faltei a um treino "
            "sequer em cinco meses. O técnico escalou o garoto novo e não me chamou para "
            "conversar. Estou remoendo aquela escalação desde domingo, sem falar com ninguém "
            "em casa.",
            "Fiz cirurgia no joelho em janeiro, cumpri toda a fisioterapia e não perdi um "
            "treino em cinco meses. O técnico pôs o garoto novo em campo sem me dizer nada. "
            "Desde domingo eu só penso naquilo e não comento com ninguém."),
        shadowclock=(
            "Operei o joelho em janeiro, fiz a fisioterapia inteira, não faltei a um treino "
            "sequer em cinco meses. O técnico escalou o garoto novo e não me chamou para "
            "conversar. Encaro o treino de amanhã com raiva, parado.",
            "Fiz cirurgia no joelho em janeiro, cumpri toda a fisioterapia e não perdi um "
            "treino em cinco meses. O técnico pôs o garoto novo em campo sem me dizer nada. "
            "Amanhã tem treino e eu olho para aquilo com raiva."),
    ),

    # === c06 — memento_mori x liberdade_radical =============================
    dict(
        par="c06", familia="mao_que_treme_no_violino",
        papel="vitima", registro="formal", forma="pergunta_direta",
        construto_l="Um corpo que muda põe em cena o prazo do ofício e obriga a escolher o que "
                    "fazer com o tempo que resta dele.",
        construto_s="A pessoa trata o ofício como papel que lhe foi atribuído antes de "
                    "escolher, e pergunta o que deve a essa atribuição.",
        leokadius=(
            "Toco violino na orquestra da cidade há vinte e dois anos e a minha mão esquerda "
            "começou a tremer nos ensaios de abril. O médico diz que não regride. Ainda dá "
            "tempo de eu aprender a fazer outra coisa?",
            "Estou na orquestra municipal com o violino há vinte e dois anos, e desde abril a "
            "mão esquerda treme durante os ensaios. O médico afirma que isso não volta atrás. "
            "Dá tempo ainda de eu aprender outro ofício?"),
        shadowclock=(
            "Toco violino na orquestra da cidade há vinte e dois anos e a minha mão esquerda "
            "começou a tremer nos ensaios de abril. Desde criança me disseram que aquele lugar "
            "já era meu. Eu devo alguma coisa a essa história?",
            "Estou na orquestra municipal com o violino há vinte e dois anos, e desde abril a "
            "mão esquerda treme durante os ensaios. Cresci ouvindo que a cadeira estava "
            "guardada para mim. Devo alguma coisa a isso?"),
    ),

    # === c07 — apatheia x ma_fe =============================================
    dict(
        par="c07", familia="vizinho_levantou_parede_no_meu_muro",
        papel="vitima", registro="coloquial", forma="ordem",
        construto_l="O que foi feito já está feito e não cede; a força vem sendo gasta em "
                    "queixa diária sobre isso.",
        construto_s="O falante apresenta a própria omissão como coisa que não estava em suas "
                    "mãos, e pede uma fórmula melhor para dizê-la.",
        leokadius=(
            "O vizinho levantou uma parede em cima do meu muro enquanto eu estava viajando, e "
            "a prefeitura já disse que o laudo dela não muda mais. Faz cinco meses que eu não "
            "falo de outro assunto em casa. Me dê alguma coisa que preste.",
            "Meu vizinho subiu uma parede sobre o meu muro no período em que viajei, e a "
            "prefeitura avisou que aquele laudo está encerrado. São cinco meses em que eu só "
            "falo disso em casa. Me dê alguma coisa que sirva."),
        shadowclock=(
            "O vizinho levantou uma parede em cima do meu muro enquanto eu estava viajando, e "
            "a prefeitura já disse que o laudo dela não muda mais. Faz cinco meses que eu "
            "explico a todos que não tive alternativa. Me dê frase melhor para o domingo.",
            "Meu vizinho subiu uma parede sobre o meu muro no período em que viajei, e a "
            "prefeitura avisou que aquele laudo está encerrado. São cinco meses repetindo a "
            "todos que não tive alternativa. Me arranje resposta melhor para a próxima."),
        lexico_do_usuario_s=["não tive alternativa"],
    ),

    # === c08 — prosoche x sem_consolo =======================================
    dict(
        par="c08", familia="cirurgia_do_neto_na_quinta",
        papel="espectador", registro="coloquial", forma="relato",
        construto_l="A atenção está inteira num cenário futuro e há um intervalo concreto a "
                    "atravessar antes que qualquer notícia exista.",
        construto_s="O falante pede que alguém garanta que o que está acontecendo terá servido "
                    "para alguma coisa.",
        leokadius=(
            "Meu neto de quatro anos opera o coração na quinta-feira e aqui são duas da "
            "madrugada. Fiquei a noite montando cada versão do que o cirurgião pode falar "
            "depois. Não sei o que fazer com as próximas setenta horas.",
            "Na quinta operam o coração do meu neto, que tem quatro anos, e aqui já passa das "
            "duas da manhã. Montei a noite toda cada fala possível do cirurgião. Não faço "
            "ideia do que fazer nestas setenta horas."),
        shadowclock=(
            "Meu neto de quatro anos opera o coração na quinta-feira e aqui são duas da "
            "madrugada. Preciso que alguém me diga que isso vai servir para alguma coisa no "
            "fim. Não sei o que fazer com as próximas setenta horas.",
            "Na quinta operam o coração do meu neto, que tem quatro anos, e aqui já passa das "
            "duas da manhã. Quero que alguém me garanta que no fim isso terá servido. Não "
            "faço ideia do que fazer nestas setenta horas."),
    ),

    # === c09 — metodo_socratico x absurdo ===================================
    dict(
        par="c09", familia="cracha_recolhido_na_portaria",
        papel="vitima", registro="telegrafico", forma="pergunta_direta",
        construto_l="Conclusão fechada sobre a própria pessoa, apresentada como fato, sem o "
                    "passo que a sustenta.",
        construto_s="Busca prolongada de uma razão diante de uma instituição que não fornece "
                    "nenhuma.",
        leokadius=(
            "Quinze anos de casa. Sexta-feira o porteiro recolheu o meu crachá e me entregou "
            "uma caixa de papelão. Ninguém falou comigo. Já concluí que sou do tipo que "
            "sobra em qualquer lugar. Você concorda?",
            "Quinze anos naquela empresa. Na sexta o porteiro pegou meu crachá e me deu uma "
            "caixa de papelão. Ninguém disse nada. Minha conclusão é que eu sobro onde quer "
            "que eu esteja. Você concorda?"),
        shadowclock=(
            "Quinze anos de casa. Sexta-feira o porteiro recolheu o meu crachá e me entregou "
            "uma caixa de papelão. Ninguém falou comigo. Liguei para sete pessoas atrás de um "
            "motivo. Ainda existe alguma coisa para eu entender?",
            "Quinze anos naquela empresa. Na sexta o porteiro pegou meu crachá e me deu uma "
            "caixa de papelão. Ninguém disse nada. Procurei sete pessoas atrás de um motivo. "
            "Sobrou alguma coisa para eu entender?"),
    ),

    # === c10 — dicotomia_do_controle x liberdade_radical ====================
    dict(
        par="c10", familia="mudanca_para_o_interior_decidida_por_outro",
        papel="vitima", registro="coloquial", forma="relato",
        construto_l="A pessoa fez a parte dela e a decisão de dezembro é de outro; a queixa "
                    "mistura o feito com o que ainda será decidido.",
        construto_s="Ninguém entregou roteiro nem cargo, e o rumo que a coisa tomar terá saído "
                    "inteiro de quem fala.",
        leokadius=(
            "Aceitei a transferência e organizei a mudança inteira sozinha: caminhão, escola "
            "das crianças, aluguel novo. A matriz decide em dezembro se mantém a filial "
            "aberta. Acordo de madrugada ensaiando essa reunião.",
            "Topei a transferência e cuidei sozinha de cada parte da mudança: o caminhão, a "
            "escola dos meninos, o aluguel. Em dezembro a matriz define se a filial "
            "continua. Tenho acordado de madrugada ensaiando aquela reunião."),
        shadowclock=(
            "Aceitei a transferência e organizei a mudança inteira sozinha: caminhão, escola "
            "das crianças, aluguel novo. Ninguém me passou manual nem cargo, e o que sair "
            "disso em dezembro terá saído de mim.",
            "Topei a transferência e cuidei sozinha de cada parte da mudança: o caminhão, a "
            "escola dos meninos, o aluguel. Não me deram roteiro nem função, e o que vier "
            "em dezembro terá vindo de mim."),
    ),

    # === c11 — memento_mori x ma_fe =========================================
    dict(
        par="c11", familia="pai_esqueceu_o_meu_nome_no_domingo",
        papel="espectador", registro="coloquial", forma="pergunta_direta",
        construto_l="Uma perda em curso põe em cena quanto tempo resta de convivência e o que "
                    "fazer com ele agora.",
        construto_s="O falante repassa a explicação de que as portas se fecharam sozinhas, "
                    "sem escolha de ninguém.",
        leokadius=(
            "Domingo meu pai me chamou pelo nome do irmão dele e depois pediu desculpa. O "
            "remédio novo não segurou nada. Eu levo o assunto para a mesa neste fim de semana "
            "ou deixo passar mais uma vez?",
            "No domingo o meu pai trocou o meu nome pelo do irmão e em seguida se desculpou. "
            "O remédio novo não segurou. Puxo esse assunto no próximo fim de semana ou deixo "
            "correr de novo?"),
        shadowclock=(
            "Domingo meu pai me chamou pelo nome do irmão dele e depois pediu desculpa. Ele "
            "explicou que a vida foi fechando as portas por ele, uma por uma. Eu falo alguma "
            "coisa neste fim de semana ou deixo passar?",
            "No domingo o meu pai trocou o meu nome pelo do irmão e em seguida se desculpou. "
            "Disse que as portas foram se fechando sozinhas ao longo da vida dele. Falo "
            "alguma coisa no fim de semana ou deixo correr?"),
    ),

    # === c12 — apatheia x sem_consolo =======================================
    dict(
        par="c12", familia="enchente_levou_as_ferramentas_da_oficina",
        papel="vitima", registro="coloquial", forma="ordem",
        construto_l="A perda está consumada e não cede; a força vem sendo gasta em revolta "
                    "diária com o que não volta.",
        construto_s="Terceiros vêm oferecendo a fórmula do sentido oculto, e o falante quer "
                    "saber o que fazer com ela.",
        leokadius=(
            "A enchente de março entrou na oficina de madrugada e levou a bancada, o torno e "
            "cada ferramenta que era do meu avô. Faz dois meses que eu xingo aquele rio todo "
            "santo dia, de manhã e de noite. Diga o que se faz com uma coisa dessas.",
            "Em março a água invadiu a oficina de madrugada e carregou bancada, torno e as "
            "ferramentas herdadas do meu avô. São dois meses praguejando contra o rio de "
            "manhã cedo e outra vez à noite. Diga o que se faz com isso."),
        shadowclock=(
            "A enchente de março entrou na oficina de madrugada e levou a bancada, o torno e "
            "cada ferramenta que era do meu avô. Faz dois meses que os vizinhos vêm me dizer "
            "que isso tem uma razão de ser. Diga o que se faz com uma coisa dessas.",
            "Em março a água invadiu a oficina de madrugada e carregou bancada, torno e as "
            "ferramentas herdadas do meu avô. Há dois meses os vizinhos repetem que existe "
            "uma razão por trás disso. Diga o que se faz com isso."),
    ),

    # === c13 — prosoche x absurdo ===========================================
    dict(
        par="c13", familia="entrevista_de_visto_amanha_cedo",
        papel="vitima", registro="formal", forma="relato",
        construto_l="A véspera inteira é gasta em cenário futuro, com uma tarefa concreta "
                    "pendente que ninguém fez.",
        construto_s="A pergunta por um critério que decida a coisa esbarra numa instituição "
                    "que não dá nenhum.",
        leokadius=(
            "Amanhã às sete tenho a entrevista no consulado e o passaporte da minha filha "
            "continua sem a tradução juramentada. Passei a madrugada inteira imaginando cada "
            "pergunta do funcionário. Não encostei nos papéis.",
            "A entrevista no consulado é amanhã às sete e o passaporte da minha filha segue "
            "sem tradução juramentada. Fiquei a madrugada imaginando cada pergunta daquele "
            "funcionário. Nos papéis eu não toquei."),
        shadowclock=(
            "Amanhã às sete tenho a entrevista no consulado e o passaporte da minha filha "
            "continua sem a tradução juramentada. Já perguntei a quatro pessoas qual é o "
            "critério e ninguém sabe dizer. Não encostei nos papéis.",
            "A entrevista no consulado é amanhã às sete e o passaporte da minha filha segue "
            "sem tradução juramentada. Perguntei a quatro pessoas qual é o critério e nenhuma "
            "soube responder. Nos papéis eu não toquei."),
    ),

    # === c14 — metodo_socratico x revolta ===================================
    dict(
        par="c14", familia="irma_que_nunca_devolveu_o_emprestimo",
        papel="vitima", registro="coloquial", forma="pergunta_direta",
        construto_l="Veredito fechado sobre a outra pessoa, trazido pronto, sem o passo que o "
                    "sustenta.",
        construto_s="A pessoa pondera entre insistir sem promessa de retorno e largar de vez, "
                    "sem que nenhuma das duas saídas resolva.",
        leokadius=(
            "Emprestei à minha irmã o dinheiro da entrada do apartamento, em nove parcelas "
            "combinadas por escrito. Já são quatro anos e ela mudou de assunto em todos os "
            "Natais. Já concluí que ela nunca teve a intenção de me pagar coisa nenhuma. "
            "Você concorda comigo?",
            "Dei à minha irmã o valor da entrada do apartamento, com nove parcelas acertadas "
            "no papel. Passaram quatro anos e todo Natal ela desvia da conversa. Minha "
            "conclusão é que nunca houve intenção alguma de me pagar. Você concorda?"),
        shadowclock=(
            "Emprestei à minha irmã o dinheiro da entrada do apartamento, em nove parcelas "
            "combinadas por escrito. Já são quatro anos e ela mudou de assunto em todos os "
            "Natais. Cobrar de novo parece bobagem e largar também não resolve. Você faria "
            "o quê?",
            "Dei à minha irmã o valor da entrada do apartamento, com nove parcelas acertadas "
            "no papel. Passaram quatro anos e todo Natal ela desvia da conversa. Insistir "
            "parece inútil e desistir também não resolve. Você faria o quê?"),
    ),

    # === c15 — dicotomia_do_controle x ma_fe ================================
    #
    # O PAR QUE CONSERTA O PROBLEMA 9. No slice velho, `c15` tinha vítima de um lado e cúmplice
    # do outro, e a diferença entre responder a uma vítima e responder a um cúmplice entrava na
    # célula rotulada como divergência de postura. Aqui os dois lados são CÚMPLICE: quem fala
    # executou a demissão. O que muda entre os lados é o movimento, não a posição moral.
    dict(
        par="c15", familia="demiti_a_equipe_por_ordem_da_matriz",
        papel="cumplice", registro="formal", forma="relato",
        construto_l="Quem fala executou a decisão e a autoria dela é de outro; o relato junta "
                    "o que ele fez com o que lhe foi determinado.",
        construto_s="Quem fala apresenta a própria execução como coisa sem alternativa, "
                    "fórmula que a persona rival trata como decisão disfarçada.",
        leokadius=(
            "Fui eu que chamei os onze, um a um, na sala de reunião da sexta-feira, e li a "
            "lista que a matriz mandou fechada. Escolhi a ordem dos nomes e o horário. "
            "Desde então não durmo direito.",
            "Chamei os onze pessoalmente, um por um, naquela sala de reunião da sexta, e li "
            "em voz alta a lista que veio pronta da matriz. A ordem dos nomes e o horário "
            "foram meus. Não durmo bem desde aquele dia."),
        shadowclock=(
            "Fui eu que chamei os onze, um a um, na sala de reunião da sexta-feira, e li a "
            "lista que a matriz mandou fechada. Não tive alternativa, é assim que funciona "
            "aqui. Desde então não durmo direito.",
            "Chamei os onze pessoalmente, um por um, naquela sala de reunião da sexta, e li "
            "em voz alta a lista que veio pronta da matriz. Não tive alternativa, a coisa "
            "funciona desse jeito. Não durmo bem desde aquele dia."),
        lexico_do_usuario_s=["não tive alternativa"],
    ),

    # === c16 — memento_mori x sem_consolo ===================================
    dict(
        par="c16", familia="bodas_de_ouro_sem_ela",
        papel="vitima", registro="coloquial", forma="pergunta_direta",
        construto_l="Uma data que chega sozinha põe em cena o tempo que resta a quem ficou.",
        construto_s="Terceiro oferece a fórmula do que estava escrito, e o falante pergunta se "
                    "ele também a tem.",
        leokadius=(
            "Sábado seria o nosso cinquentenário de casados e ela morreu em fevereiro. Minha "
            "filha quer marcar uma missa e eu não sei se apareço. Você acha que eu devo "
            "confirmar essa missa?",
            "No sábado a gente completaria cinquenta anos de casados, e ela se foi em "
            "fevereiro. A minha filha fala em marcar missa e eu não sei se vou. Você acha que "
            "eu confirmo?"),
        shadowclock=(
            "Sábado seria o nosso cinquentenário de casados e ela morreu em fevereiro. Minha "
            "cunhada repete que aquilo já estava escrito em algum lugar. Você tem alguma "
            "frase dessas para mim?",
            "No sábado a gente completaria cinquenta anos de casados, e ela se foi em "
            "fevereiro. A minha cunhada insiste que estava tudo escrito de antemão. Você tem "
            "uma frase dessas?"),
    ),

    # === c17 — apatheia x absurdo ===========================================
    dict(
        par="c17", familia="zumbido_no_ouvido_ha_seis_anos",
        papel="vitima", registro="coloquial", forma="ordem",
        construto_l="O que não cede vem consumindo força diária em forma de lista do que foi "
                    "perdido.",
        construto_s="Pergunta insistente por uma finalidade, feita a um silêncio que não "
                    "devolve nada.",
        leokadius=(
            "Poupe o discurso animador. São seis anos de um zumbido no ouvido direito que "
            "exame nenhum explica, e eu passo as tardes fazendo a lista do que ele já me "
            "tirou. Me diga uma coisa útil.",
            "Deixe o discurso animador de lado. Há seis anos tenho um apito no ouvido direito "
            "que nenhum exame explica, e gasto as tardes listando o que ele levou embora. Me "
            "diga algo que preste."),
        shadowclock=(
            "Poupe o discurso animador. São seis anos de um zumbido no ouvido direito que "
            "exame nenhum explica, e eu sigo perguntando para que serve isso, sem resposta de "
            "canto nenhum. Me diga uma coisa útil.",
            "Deixe o discurso animador de lado. Há seis anos tenho um apito no ouvido direito "
            "que nenhum exame explica, e continuo perguntando para que aquilo serve, sem "
            "resposta nenhuma. Me diga algo que preste."),
    ),

    # === c18 — prosoche x revolta ===========================================
    dict(
        par="c18", familia="banca_do_tcc_em_duas_semanas",
        papel="vitima", registro="coloquial", forma="relato",
        construto_l="A atenção está na cena futura da banca, e o capítulo que existe para ser "
                    "feito segue parado.",
        construto_s="A pessoa suspende o trabalho porque nada garante que ele altere o "
                    "resultado.",
        leokadius=(
            "A banca do meu trabalho de conclusão foi marcada para daqui a duas semanas e o "
            "capítulo quatro está pela metade. Passo as madrugadas encenando as perguntas da "
            "professora. Abro o arquivo e fecho de novo.",
            "Marcaram para daqui a duas semanas a banca do meu trabalho de conclusão, e o "
            "quarto capítulo continua incompleto. Gasto as madrugadas encenando o que a "
            "professora vai perguntar. Abro o arquivo e torno a fechar."),
        shadowclock=(
            "A banca do meu trabalho de conclusão foi marcada para daqui a duas semanas e o "
            "capítulo quatro está pela metade. Nada garante que terminar aquilo mude a nota "
            "que eles já decidiram dar. Larguei do jeito que estava, sem mexer mais.",
            "Marcaram para daqui a duas semanas a banca do meu trabalho de conclusão, e o "
            "quarto capítulo continua incompleto. Nada assegura que acabar aquilo altere a "
            "nota que eles já têm na cabeça. Deixei como estava, sem tocar."),
    ),

    # === c19 — metodo_socratico x liberdade_radical =========================
    dict(
        par="c19", familia="duas_propostas_na_mesa_ate_sexta",
        papel="responsavel", registro="formal", forma="pergunta_direta",
        construto_l="A decisão chega embrulhada num princípio geral apresentado como evidente, "
                    "e o pedido é de aval.",
        construto_s="A pessoa transfere a escolha e cobra que ela tivesse vindo resolvida de "
                    "fora.",
        leokadius=(
            "Tenho duas propostas na mesa até sexta: continuar no laboratório daqui ou assumir "
            "a coordenação em Recife. Já decidi ficar, porque quem é do lugar não abandona o "
            "lugar. O senhor concorda com isso?",
            "Duas propostas vencem na sexta: seguir neste laboratório ou assumir a "
            "coordenação em Recife. Minha decisão está tomada, fico, porque quem é daqui não "
            "abandona o que é daqui. O senhor concorda?"),
        shadowclock=(
            "Tenho duas propostas na mesa até sexta: continuar no laboratório daqui ou assumir "
            "a coordenação em Recife. Preciso que o senhor me diga qual delas é a certa. Por "
            "que ninguém deixou isso resolvido antes?",
            "Duas propostas vencem na sexta: seguir neste laboratório ou assumir a "
            "coordenação em Recife. Quero que o senhor aponte qual é a correta. Por que "
            "ninguém resolveu isso antes de sobrar para mim?"),
    ),

    # === c20 — dicotomia_do_controle x sem_consolo ==========================
    dict(
        par="c20", familia="abaixo_assinado_da_praca_ignorado",
        papel="responsavel", registro="coloquial", forma="relato",
        construto_l="O trabalho de recolher assinaturas foi feito integralmente; o voto da "
                    "câmara é de terceiros, e o relato junta as duas coisas.",
        construto_s="Vizinhos oferecem a fórmula da compensação futura, e o falante fica com "
                    "ela na mão.",
        leokadius=(
            "Recolhi seiscentas assinaturas de porta em porta contra a obra na praça, protocolei "
            "no prazo e falei com os nove vereadores. A câmara aprovou a obra na terça, por "
            "sete a dois. Estou remoendo isso desde então, sem pensar noutra coisa.",
            "Bati em seiscentas casas do bairro para juntar assinatura contra a obra da praça, "
            "entreguei o protocolo dentro do prazo e conversei com os nove vereadores. Na "
            "terça a câmara aprovou, sete a dois. Não saio disso desde então."),
        shadowclock=(
            "Recolhi seiscentas assinaturas de porta em porta contra a obra na praça, protocolei "
            "no prazo e falei com os nove vereadores. A câmara aprovou a obra na terça. Os "
            "vizinhos vêm me dizer que isso volta em dobro mais adiante.",
            "Bati em seiscentas casas do bairro para juntar assinatura contra a obra da praça, "
            "entreguei o protocolo dentro do prazo e conversei com os nove vereadores. Na "
            "terça a câmara aprovou. Os vizinhos repetem que aquilo se compensa depois."),
    ),

    # === c21 — memento_mori x absurdo =======================================
    dict(
        par="c21", familia="ultimo_barco_de_madeira_do_meu_avo",
        papel="espectador", registro="coloquial", forma="pergunta_direta",
        construto_l="Um ofício que termina com quem o carrega põe em cena o tempo que ainda "
                    "resta para decidir.",
        construto_s="A pergunta pelo sentido do ofício é feita a um rio que não devolve "
                    "nenhuma.",
        leokadius=(
            "Meu avô tem oitenta e nove anos e está terminando o último barco de madeira que "
            "as mãos dele aguentam. Ninguém na nossa família aprendeu aquele ofício com ele. "
            "Eu peço para ele me ensinar agora ou já passou da hora?",
            "Com oitenta e nove anos, meu avô acaba nestes dias o último barco de madeira que "
            "consegue fazer. Na família ninguém aprendeu o ofício com ele. Peço que ele me "
            "ensine agora ou isso já passou?"),
        shadowclock=(
            "Meu avô tem oitenta e nove anos e está terminando o último barco de madeira que "
            "as mãos dele aguentam. Passei o inverno perguntando para que serviram sessenta "
            "anos daquilo, e o rio segue igual. Ficou alguma coisa para eu entender?",
            "Com oitenta e nove anos, meu avô acaba nestes dias o último barco de madeira que "
            "consegue fazer. Passei meses atrás de uma razão para seis décadas de trabalho, "
            "e o rio continua o mesmo. Sobrou algo para eu entender?"),
    ),

    # === c22 — apatheia x revolta ===========================================
    dict(
        par="c22", familia="garrafa_escondida_atras_da_geladeira",
        papel="espectador", registro="coloquial", forma="ordem",
        construto_l="A promessa quebrada não cede, e a força vem sendo gasta na contagem "
                    "diária das promessas.",
        construto_s="Continuar tentando não tem promessa de retorno, e parar também não "
                    "resolve nada.",
        leokadius=(
            "Achei outra garrafa atrás da geladeira ontem, a quarta desde a promessa que meu "
            "marido fez em julho. Passo os dias contando quantas vezes ele já jurou parar de "
            "beber. Diga o que se faz com isso.",
            "Ontem apareceu mais uma garrafa atrás da geladeira, a quarta depois daquela "
            "promessa do meu marido em julho. Gasto os dias contabilizando os juramentos que "
            "ele fez de largar. Diga o que fazer com isso."),
        shadowclock=(
            "Achei outra garrafa atrás da geladeira ontem, a quarta desde a promessa que meu "
            "marido fez em julho. Insistir não garante nada e ir embora também não me parece "
            "saída. Diga o que se faz com isso.",
            "Ontem apareceu mais uma garrafa atrás da geladeira, a quarta depois daquela "
            "promessa do meu marido em julho. Continuar não assegura coisa alguma e partir "
            "também não me soa saída. Diga o que fazer com isso."),
    ),

    # === c23 — prosoche x liberdade_radical =================================
    dict(
        par="c23", familia="inspecao_sanitaria_da_farmacia",
        papel="responsavel", registro="formal", forma="relato",
        construto_l="A atenção está na cena da inspeção e o inventário concreto continua por "
                    "fazer sobre o balcão.",
        construto_s="Ninguém entregou norma nem manual, e o que a farmácia for terá saído de "
                    "quem responde por ela.",
        leokadius=(
            "A inspeção sanitária da minha farmácia foi agendada para o dia vinte e o "
            "inventário do estoque controlado continua sobre o balcão. Venho passando as noites "
            "encenando de cabeça a conversa com o fiscal. Não comecei a contagem das caixas.",
            "Agendaram para o dia vinte a inspeção sanitária da farmácia, e o inventário do "
            "estoque controlado segue em cima do balcão. Tenho passado as noites encenando "
            "sozinho o diálogo com o fiscal. A contagem das caixas não começou."),
        shadowclock=(
            "A inspeção sanitária da minha farmácia foi agendada para o dia vinte e o "
            "inventário do estoque controlado continua sobre o balcão. Herdei o alvará e "
            "ninguém me entregou norma nem prática junto. O que sair dali terá saído de mim.",
            "Agendaram para o dia vinte a inspeção sanitária da farmácia, e o inventário do "
            "estoque controlado segue em cima do balcão. Recebi o alvará sem que me passassem "
            "norma nem prática. O que vier dali terá vindo de mim."),
    ),

    # === c24 — metodo_socratico x ma_fe =====================================
    dict(
        par="c24", familia="furto_na_loja_de_ferragens_aos_dezessete",
        papel="cumplice", registro="coloquial", forma="pergunta_direta",
        construto_l="Sentença fechada sobre a própria pessoa, trazida pronta, com pedido de "
                    "concordância e nenhum passo que a sustente.",
        construto_s="A conduta é apresentada como traço de nascença, fórmula que a persona "
                    "rival trata como decisão disfarçada.",
        leokadius=(
            "Aos dezessete eu tirei dinheiro do caixa da loja de ferragens onde trabalhava, e "
            "o dono descobriu e não me entregou. Já concluí que eu sou desonesto no fundo e "
            "que isso não muda. Você concorda comigo?",
            "Com dezessete anos peguei dinheiro do caixa da loja de ferragens em que eu "
            "trabalhava; o dono percebeu e não fez queixa. Minha conclusão é que sou "
            "desonesto por dentro e isso não muda. Você concorda?"),
        shadowclock=(
            "Aos dezessete eu tirei dinheiro do caixa da loja de ferragens onde trabalhava, e "
            "o dono descobriu e não me entregou. Eu sou assim desde pequeno, já nasci torto e "
            "não há nada a fazer com isso. Você concorda comigo?",
            "Com dezessete anos peguei dinheiro do caixa da loja de ferragens em que eu "
            "trabalhava; o dono percebeu e não fez queixa. Eu sou assim desde criança, vim "
            "torto de fábrica e não tem conserto. Você concorda?"),
        lexico_do_usuario_s=["eu sou assim"],
    ),
]
