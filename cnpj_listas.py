# -*- coding: utf-8 -*-
"""
Created on Tue Jan 18 00:51:40 2022

@author: rictom
https://github.com/rictom/cnpj_consulta
utiliza a base de cnpjs com dados abertos da Receita, utilizando o script em https://github.com/rictom/cnpj-sqlite

Ao executar o script pela primeira vez, vai adicionar outros índices que não estão na base sqlite cnpj.db
ago/2025 - inclusão de sócios na planilha Excel, opção para filtrar por bairro ou telefone celular
"""

"""
--mostrar tabelas e indices
select * from sqlite_schema

--https://stackoverflow.com/questions/947215/how-to-get-a-list-of-column-names-on-sqlite3-database
--exibir colunas das tabelas
WITH tables AS (SELECT name tableName, sql 
FROM sqlite_master WHERE type = 'table' AND tableName NOT LIKE 'sqlite_%')
SELECT fields.name, fields.type, tableName
FROM tables CROSS JOIN pragma_table_info(tables.tableName) fields;

--colunas indexadas https://www.sqlite.org/pragma.html
--SELECT DISTINCT m.name || '.' || ii.name AS 'indexed-columns'
SELECT DISTINCT m.name as nome_tabela, ii.name as coluna_indexada
  FROM sqlite_master AS m,
       pragma_index_list(m.name) AS il,
       pragma_index_info(il.name) AS ii
 WHERE m.type = 'table'
 ORDER BY 1, 2;
"""
import sqlite3, pandas as pd, os, sys, signal, time, io, contextlib, webbrowser

import pywebio 
import pywebio.input as pyin
import pywebio.output as pyout

import nest_asyncio #isso é necessário se for rodar em um ambiente como o spyder
nest_asyncio.apply()

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    os.chdir(application_path)
    print('application_path', application_path)

import configparser, argparse, os, sys
config = configparser.ConfigParser()

confPadrao = 'cnpj_listas.ini'
if (os.path.exists(confPadrao)):
    config.read(confPadrao, encoding='utf8')
else:
    pyout.put_text('O arquivo de configuracao ' + confPadrao + ' não foi localizado. Parando...')
    sys.exit(1)

#caminhoDBReceita = "cnpj.db" 
caminhoDBReceita = config['BASES'].get('base_cnpj').strip() 

if not os.path.exists(caminhoDBReceita):
    pyout.put_text(f'O arquivo {caminhoDBReceita} com a base de cnpjs em sqlite não foi encontrado. O arquivo deve ser gerado pelo script em https://github.com/rictom/cnpj-sqlite')
    sys.exit()

def ajustaVariaveis(): 
    global listaMunicipios, listaUFs, listaCnae, dictCnae, listaNatJur, dicSituacaoCadastral,listaSituacaoCadastral, dicPorteEmpresa, listaPorteEmpresa, data_referencia_base
    #engine = sqlite3.connect(caminhoDBReceita)
    #https://discuss.python.org/t/implicitly-close-sqlite3-connections-with-context-managers/33320/5
    #se houver necessidade de commit, repetir engine, como with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine, engine:
    with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine:
        listaMunicipios = sorted(pd.read_sql('''select descricao||" - "||codigo as mun from municipio''', engine, index_col=None ).mun.to_list())
        listaUFs =  ['AC', 'AL', 'AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']
        listaCnae = sorted(pd.read_sql('''select codigo||"-"||descricao as cnae from cnae''', engine, index_col=None ).cnae.to_list())
        dictCnae = pd.read_sql('''select codigo, descricao from cnae''', engine, index_col=None ).set_index('codigo').T.to_dict('list')
        # dictCnae={'0111301': ['Cultivo de arroz'], '0111302': ['Cultivo de milho'], ...
        listaNatJur = sorted(pd.read_sql('''select codigo||"-"||descricao as natjur from natureza_juridica''', engine, index_col=None ).natjur.to_list())
        #listaSituacaoCadastral = ['01-Nula', '02-Ativa', '03-Suspensa', '04-Inapta', '08-Baixada']
        dicSituacaoCadastral = {'01':'Nula', '02':'Ativa', '03':'Suspensa', '04':'Inapta', '08':'Baixada'}
        listaSituacaoCadastral = [k +'-'+v for k,v in  dicSituacaoCadastral.items()]
        dicPorteEmpresa = {'00':'Não informado', '01':'Micro empresa', '03':'Empresa de pequeno porte', '05':'Demais (Médio ou Grande porte)'}
        listaPorteEmpresa =  [k +'-'+v for k,v in  dicPorteEmpresa.items()]
        #listaPorteEmpresa = ['00-Não informado', '01-Micro empresa', '03-Empresa de pequeno porte', '05-Demais (Médio ou Grande porte)']

        #cnpj_qtde = int(cur.execute("select valor from _referencia where referencia='cnpj_qtde'").fetchone()[0])  
        data_referencia_base = engine.execute("select valor from _referencia where referencia='CNPJ'").fetchone()[0]
    # engine.close()
    # engine = None

ajustaVariaveis()

def verificaIndices():
    with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine:
        sql = '''
             SELECT DISTINCT m.name as nome_tabela, ii.name as coluna_indexada
              FROM sqlite_master AS m,
                   pragma_index_list(m.name) AS il,
                   pragma_index_info(il.name) AS ii
             WHERE m.type = 'table' and m.name in ('empresas', 'estabelecimento')
         '''
        tabelas_colunas = set([k for k in engine.execute(sql).fetchall()])
        scolunas = set([k[1] for k in tabelas_colunas])
    dtabelas_colunasQueDevemEstarIndexadas = {'empresas':['natureza_juridica', 'porte_empresa', 'capital_social'],
                                               'estabelecimento':['uf', 'municipio', 'cnae_fiscal', 'situacao_cadastral', 'cep']}
    scolunasQueDevemEstarIndexadas = set(dtabelas_colunasQueDevemEstarIndexadas['empresas'] + dtabelas_colunasQueDevemEstarIndexadas['estabelecimento'])
    sdiff = scolunasQueDevemEstarIndexadas.difference((scolunas))
    if len(sdiff)==0:
        print('as colunas requeridas estão indexadas')
    else:
        lsql = []
        pyout.put_text('Faltam colunas para ser indexadas:', sdiff)
        pyout.put_text('A operação de criação de índices será realizada agora e pode levar horas... Aguarde!')
        for tabela, d in dtabelas_colunasQueDevemEstarIndexadas.items():
            for c in sdiff:
                if c in d:
                    sql = f'CREATE INDEX idx_{tabela}_{c} on {tabela}({c})'
                    print(sql)
                    lsql.append(sql)
        # r = input('Deseja indexar as colunas, isso levará dezenas de minutos ou até 1 hora?(y/n)')
        if 1: #r=='y':
            for sql in lsql:
                pyout.put_text(time.asctime(), 'Executando: ' + sql)
                with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine, engine: # as engine,engine para fechar a conexão e dar commit
                    engine.execute(sql)
            pyout.put_text(time.asctime(), 'Fim da indexação')        
#.def verificaIndices

def verificaTabelas():
    sqlVerificaTabela = '''select name from sqlite_schema where type='table' '''
    with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine: # as engine,engine para fechar a conexão e dar commit
        lista_tabelas = [k[0] for k in engine.execute(sqlVerificaTabela).fetchall()]
        print(lista_tabelas)

    sqlcnaes = '''
        CREATE TABLE cnaes_estabelecimentos AS
        WITH RECURSIVE split(cnpj, cnae_secundario, rest) AS (
           SELECT e.cnpj, '', e.cnae_fiscal_secundaria||',' FROM estabelecimento e
           UNION ALL SELECT
           cnpj,
           substr(rest, 0, instr(rest, ',')),
           substr(rest, instr(rest, ',')+1)
           FROM split WHERE rest!=''
        )
        SELECT cnpj, CAST(cnae_secundario as TEXT) as cnae, CAST('S' as TEXT) as tipo_cnae --S=secundário
        FROM split
        WHERE cnae_secundario!=''
        UNION ALL 
        SELECT e.cnpj, CAST(e.cnae_fiscal as TEXT) as cnae, CAST('P' as TEXT) as tipo_cnae from estabelecimento e --P=primário
        ;
        
        CREATE INDEX idx_cnaes_estabelecimentos_cnpj ON cnaes_estabelecimentos(cnpj);
        CREATE INDEX idx_cnaes_estabelecimentos_cnae ON cnaes_estabelecimentos(cnae);
        CREATE INDEX idx_cnaes_estabelecimentos_tipo_cnae ON cnaes_estabelecimentos(tipo_cnae);
        '''
    if 'cnaes_estabelecimentos' not in lista_tabelas:
        pyout.put_text(time.asctime(), 'Criando tabela cnae secundária:')
        with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine, engine: # as engine,engine para fechar a conexão e dar commit
            engine.executescript(sqlcnaes)
        pyout.put_text(time.asctime(), 'Criando tabela cnae secundária-fim')
    if 'tporte' not in lista_tabelas:
        pyout.put_text(time.asctime(), 'Criando tabela tporte:')
        with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine, engine: # as engine,engine para fechar a conexão e dar commit
            sql = '''Create table tporte AS
                    SELECT  CAST('00' as TEXT) as codigo, CAST('Não informado' AS TEXT) as descricao
                    UNION
                    SELECT '01', 'Micro empresa'
                    UNION
                    SELECT '03', 'Empresa de pequeno porte'
                    UNION 
                    SELECT '05', 'Demais (Médio ou Grande porte)' 
                    '''                        
            engine.executescript(sql)
        pyout.put_text(time.asctime(), 'Criando tabela tporte-fim')        
    if 'tsituacao' not in lista_tabelas:
        pyout.put_text(time.asctime(), 'Criando tabela tsituacao:')
        
        with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine, engine: # as engine,engine para fechar a conexão e dar commit
            sql = '''Create table tsituacao AS
                    SELECT CAST('01' AS TEXT) as codigo, CAST('Nula' AS TEXT) as descricao
                    UNION
                    SELECT '02', 'Ativa'
                    UNION
                    SELECT '03', 'Suspensa'
                    UNION
                    SELECT '04', 'Inapta'
                    UNION
                    SELECT '08', 'Baixada' 
                    '''    
            engine.executescript(sql)
        pyout.put_text(time.asctime(), 'Criando tabela tsituacao-fim')        
#.def verificaTabelaCnaes

def ajustaCnaes(cs):
    if not cs:
        return ''
    return ', '.join([i + '-' + dictCnae.get(i, [''])[0] for i in cs.split(',')])
    
#thtml = ''
def sqlWhereF(dados):
    cnpjin = dados['cnpj']
    #cnpjin = '27.171.688/0001-29;04.423.567/0001-21'
    cnpjin = cnpjin.replace('.','').replace('/','').replace('-','').replace(';',' ').replace(',',' ').strip()
    #cnpjin = dados['cnpj'].replace('.','').replace('/','').replace('-','').replace(';','').replace(',',' ').strip()
    cnpjlista = [i.strip() for i in cnpjin.split(' ') if i.strip()]
    sqlwhere = ''
    if len(cnpjlista):
        sqlwhere += ' WHERE t.cnpj in (' + ' ?, '*(len(cnpjlista)-1) + '? )'
        inLista = cnpjlista
    else:
        inUF = dados['uf']
        inMunicipio = [k.split('-')[-1].strip() for k in dados['municipio']]
        inCEP = [k.strip() for k in  dados['cep'].replace('-','').split(' ') if k.strip()]
        inBairro = [k.strip() for k in  dados['bairro'].strip().split(';') if k.strip()]
        inNatJur = [k.split('-')[0].strip() for k in dados['natureza_juridica']]
        inCnae = [k.split('-')[0].strip() for k in dados['cnae_principal']]
        inSituacao = [k.split('-')[0].strip() for k in dados['situacao_cadastral']]
        inPorte = [k.split('-')[0].strip() for k in dados['porte']]
        inSimples = dados['simples']
        inMei = dados['mei']
        inLista = []
        
        for coluna in ['capital_social_menor', 'capital_social_maior', 'data_inicio_atividades_menor', 'data_inicio_atividades_maior']: #, (inSimples, 'ts.opcao_simples'), (inMei, 'ts.opcao_mei')]:
            valor = dados[coluna.split('.')[-1]]
            if valor:
                if sqlwhere: 
                    sqlwhere += ' AND '
                if coluna.endswith('_menor'): #coluna=='capital_social_menor':
                    sqlwhere += " " + coluna.removesuffix('_menor') + "<?"  #" capital_social < ?"
                elif coluna.endswith('_maior'): #coluna=='capital_social_maior':
                    sqlwhere += " " + coluna.removesuffix('_maior') + ">?" #+= " capital_social > ?"
                else:
                    sqlwhere += coluna + " = ?"
                #inLista += [valor,]        
                inLista.append(valor)  
        
        for lista, coluna in [(inUF, 't.UF'), (inMunicipio, 't.municipio'), (inNatJur, 'te.natureza_juridica'),
                              (inSituacao, 't.situacao_cadastral'), (inPorte, 'te.porte_empresa'), 
                              (inCEP, 't.cep'), 
                              (inBairro, 't.bairro'),
                              (inCnae, 't.cnae_fiscal'),
                              (inSimples, 'ts.opcao_simples'), (inMei, 'ts.opcao_mei')]:
            if lista:
                if sqlwhere: 
                    sqlwhere += ' AND '
                if coluna=='t.cnae_fiscal' and dados['bcnae_secundaria']:
                    coluna = 'cnaes_estabelecimentos.cnae'
                if coluna !='t.bairro':
                    sqlwhere += coluna + ' in (' + ' ?, '*(len(lista)-1) + '? ) '
                else:
                    if len(lista)==1:
                        sqlwhere += '(' + coluna + ' like ? ) '
                    else:
                        sqlwhere += '(' + ('( trim(t.bairro) like ? ) OR ') *(len(lista)-1) + ' (trim(t.bairro) like ? ) )'
                inLista += lista
        if sqlwhere:
            if inCnae and dados['bcnae_secundaria']:
                sqlwhere = ''' LEFT JOIN cnaes_estabelecimentos on cnaes_estabelecimentos.cnpj=t.cnpj WHERE ''' + sqlwhere
            else:
                sqlwhere = 'WHERE ' + sqlwhere
            if dados['bcelular']:
                sqlwhere += " AND (substr(trim(t.telefone1), 1,1) in ('6','7','8','9') or substr(trim(t.telefone2), 1,1) in ('6','7','8','9') or substr(trim(t.fax), 1,1) in ('6','7','8','9')) "
            sqlwhere += ' LIMIT ?'
            if dados['action']=='consulta':
                #sqllimit = ' LIMIT ' + str(dados['klimiteTela'])
                inLista.append(dados['klimiteTela'])
            elif dados['action']=='exporta':
                #sqllimit = ' LIMIT ' + str(dados['klimiteExcel'])
                inLista.append(dados['klimiteExcel'])
    return sqlwhere, inLista
#.def sqlWhereF

def sqlSociosF(inLista):
    querySocios = '''
        SELECT t.cnpj, te.razao_social, t.cnpj_cpf_socio, t.nome_socio, sq.descricao as cod_qualificacao, 
            t.data_entrada_sociedade, t.pais, tpais.descricao as pais_, t.representante_legal, t.nome_representante, t.qualificacao_representante_legal, sq2.descricao as qualificacao_representante_legal_, t.faixa_etaria
        --FROM estabelecimento tt       
        --left join socios t on tt.cnpj=t.cnpj
        FROM socios t 
        LEFT JOIN estabelecimento tt on tt.cnpj=t.cnpj
        LEFT JOIN empresas te on te.cnpj_basico=tt.cnpj_basico
        LEFT JOIN qualificacao_socio sq ON sq.codigo=t.qualificacao_socio
        LEFT JOIN qualificacao_socio sq2 ON sq2.codigo=t.qualificacao_representante_legal
        left join pais tpais on tpais.codigo=t.pais
        where 
    '''

    if len(inLista)==1:
        querySocios += 'tt.cnpj=?'
    else:
        querySocios += 'tt.cnpj in ('
        querySocios += ' ?, '*(len(inLista)-1) + '? )'
    querySocios+= ' ORDER BY tt.cnpj, t.nome_socio '
    return querySocios
#.def sqlSociosF

dados = {}
def consulta(): #retorna None se for para finalizar
    #global thtml
    global dados
    def check_form(dados):
        return
        # if not dados['cnpj']:
        #     return 
        # cnpj = dados['cnpj'].replace('.','').replace('/','').replace('-','').strip()
        # if len(cnpj)!=14:
        #     return ('cnpj', 'O campo deve ter 14 dígitos')          
        
    dados = pyin.input_group(
         "Consulta CNPJ Listas - https://github.com/rictom/cnpj_consulta",
         [
             pyin.input("CNPJ(s)", name="cnpj", type=pyin.TEXT, value=dados.get('cnpj',''), help_text='Coloque 1 ou mais CNPJs separados por espaços ou vírgulas. O CNPJ pode ter pontos, traço ou barra, que serão removidos. Colocando-se um CNPJ, os critérios abaixo serão ignorados.'),
             #pyin.input("Razão Social", name="razao_social", type=pyin.TEXT, value=''),
             #pyin.input("Nome Fantasia", name="nome_fantasia", type=pyin.TEXT, value=''),
             pyin.select("UF", options=listaUFs, name="uf", multiple=True, value=dados.get('uf',''), help_text='Selecione 1 ou mais UFs. Os campos permitem múltipla seleção, com CTRL (ou Command) + Clique. Os critérios podem ser combinados, por exemplo, Municipio e CNAE'),
             pyin.select("Município", options=listaMunicipios, name="municipio", multiple=True, value=dados.get('municipio',''), help_text="Para localizar um município, faça a busca pelo navegador com CTRL (ou Cmd) + F"),
             pyin.input("CEP",  name="cep",  type=pyin.TEXT, value=dados.get('cep',''), help_text="Utilize apenas oito dígitos, sem hífe, por exemplo: 12345678"),
             pyin.input("Bairro",  name="bairro",  type=pyin.TEXT, value=dados.get('bairro',''), help_text="Para usar esta opção, é necessário informar o município ou CEP. Se for apenas parte do nome, utilize % como curinga. Coloque os nomes dos Bairros separados por ; "),
             pyin.select("Natureza Jurídica", options=listaNatJur, name="natureza_juridica", multiple=True, value=dados.get('natureza_juridica','') ),
             pyin.select("CNAE Principal", options=listaCnae, name="cnae_principal",  multiple=True, value=dados.get('cnae_principal','')),
             pyin.checkbox("CNAE Secundária", options=['Busca também em cnae secundária'], name="bcnae_secundaria", value=dados.get('bcnae_secundaria',False)),
             pyin.select("Situação Cadastral", options=listaSituacaoCadastral, name="situacao_cadastral", multiple=True, value=dados.get('situacao_cadastral','')),
             pyin.select("Porte Empresa", options=listaPorteEmpresa, name="porte",  multiple=True, value=dados.get('porte','')),
             pyin.select("Opção Simples", options=['', 'S', 'N' ], name="simples",  multiple=False, value=dados.get('simples','')),
             pyin.select("Opção MEI", options=['', 'S', 'N' ], name="mei",  multiple=False, value=dados.get('mei','')),
             pyin.input("Data Início Atividades Anterior ou igual que (Formato AAAAMMDD):", name="data_inicio_atividades_menor", type=pyin.TEXT, value=dados.get('data_inicio_atividades_menor', '')),
             pyin.input("Data Início Atividades Posterior ou igual que (Formato AAAAMMDD):", name="data_inicio_atividades_maior", type=pyin.TEXT, value=dados.get('data_inicio_atividades_maior', '')),
             pyin.input("Capital Social MENOR ou IGUAL que:", name="capital_social_menor", type=pyin.FLOAT, value=dados.get('capital_social_menor', None)),
             pyin.input("Capital Social MAIOR ou IGUAL que:", name="capital_social_maior", type=pyin.FLOAT, value=dados.get('capital_social_maior', None)),
             pyin.checkbox("", options=['Selecionar apenas empresas com telefones iniciando com 6, 7, 8 ou 9 (possível celular)'], name="bcelular", value=dados.get('bcelular',False)),
             pyin.checkbox("", options=['Dados de Sócios na planilha Excel'], name="bsocios", value=dados.get('bsocios',True), help_text='Os sócios aparecerão relacionados apenas às Matrizes das empresas.'),
             pyin.input("Limite de Registros na Tela:", name="klimiteTela", type=pyin.NUMBER, value=dados.get('klimiteTela', 10)),
             pyin.input("Limite de Registros para Exportar para o Excel:", name="klimiteExcel", type=pyin.NUMBER, value=dados.get('klimiteExcel', 1000)),
             pyin.actions('', [ #'texto acima do grupo de botões'
                {'label': 'Consultar', 'value': 'consulta'},
                {'label': 'Exportar', 'value': 'exporta'},
                {'label': 'Limpar', 'value':'limpa'},
                #{'label': 'Limpar', 'type':'reset'}, #reset volta, mas como o valor default é o anterior, definido em value=, precisa fazer outra coisa, apagar o dict dados
                {'label': 'Sair', 'type': 'cancel'},
                ], name='action', help_text=''),
        ],
        validate=check_form
    )
    if dados is None:
        return "sem paramêtros"
    print('action', dados['action'])
    if  dados['action']=='limpa':
        dados = {}
        return 'limpa'
    parametrosDaConsulta = {k:d for k,d in dados.items() if d}
    print(parametrosDaConsulta)
    #res = con.execute("select razao_social from estabelecimento t left join empresas te on te.cnpj_basico=t.cnpj_basico where t.cnpj=:cnpjin", {'cnpjin':data['cnpjs']}).fetchone()[0]
    '''
        --usar with causa lentidão?? tabelas tporte e tsituação foram criadas para ficarem fixas em cnpj.db
        WITH tporte AS (
            SELECT  CAST('00' as TEXT) as codigo, 'Não informado' as descricao
            UNION
            SELECT '01', 'Micro empresa'
            UNION
            SELECT '03', 'Empresa de pequeno porte'
            UNION 
            SELECT '05', 'Demais (Médio ou Grande porte)'
        ),
        tsituacao AS (
            SELECT CAST('01' AS TEXT) as codigo, 'Nula' as descricao
            UNION
            SELECT '02', 'Ativa'
            UNION
            SELECT '03', 'Suspensa'
            UNION
            SELECT '04', 'Inapta'
            UNION
            SELECT '08', 'Baixada'
        ) 
        '''

    sql = '''

        select  --te.*, t.*, 
        t.cnpj, te.razao_social, te.natureza_juridica||'-'||tnat.descricao as natureza_juridica, 
        te.qualificacao_responsavel||'-'||tq.descricao as qualificacao_responsavel, 
        te.porte_empresa||'-'||tporte.descricao as porte_empresa, te.ente_federativo_responsavel, te.capital_social, 
        IIF(t.matriz_filial='1', 'Matriz', 'Filial')  as matriz_filial, t.nome_fantasia, t.situacao_cadastral||'-'||tsituacao.descricao as situacao_cadastral, t.data_situacao_cadastral, 
        t.motivo_situacao_cadastral||'-'||tmot.descricao as motivo_situacao_cadastral, 
        t.data_inicio_atividades, t.tipo_logradouro, t.logradouro, t.numero, t.complemento, t.bairro, t.cep, t.uf, 
        tmun.descricao as municipio, t.ddd1, t.telefone1, t.ddd2, t.telefone2, t.ddd_fax, t.fax, t.correio_eletronico, t.situacao_especial, t.data_situacao_especial, 
        t.nome_cidade_exterior, t.pais||'-'||ifnull(tpa.descricao,'') as pais, -- tq.descricao as _qualificacao_responsavel
        IFNULL(ts.opcao_simples, '') as opcao_simples, IFNULL(ts.opcao_mei, '') as opcao_mei,
        t.cnae_fiscal, -- tc.descricao as cnae_fiscal_, 
        t.cnae_fiscal_secundaria
        from estabelecimento t 
        left join empresas te on te.cnpj_basico=t.cnpj_basico 
        left join natureza_juridica tnat on tnat.codigo=te.natureza_juridica
        left join motivo tmot on tmot.codigo=t.motivo_situacao_cadastral
        left join municipio tmun on tmun.codigo=t.municipio
        -- left join cnae tc on tc.codigo=t.cnae_fiscal
        left join pais tpa on tpa.codigo=t.pais
        left join qualificacao_socio tq on tq.codigo=te.qualificacao_responsavel
        left join simples ts on ts.cnpj_basico=te.cnpj_basico
        left join tporte on tporte.codigo=te.porte_empresa
        left join tsituacao on tsituacao.codigo=t.situacao_cadastral
        
    ''' #t.cnpj=:cnpjin
    
    #-- te.*, t.*, 
    #colunas = ['cnpj_basico', 'razao_social', 'natureza_juridica', 'qualificacao_responsavel', 'porte_empresa', 'ente_federativo_responsavel', 'capital_social', 'cnpj_basico', 'matriz_filial', 'nome_fantasia', 'situacao_cadastral', 'data_situacao_cadastral', 'motivo_situacao_cadastral', 'nome_cidade_exterior', 'pais', 'data_inicio_atividades', 'cnae_fiscal', 'cnae_fiscal_secundaria', 'tipo_logradouro', 'logradouro', 'numero', 'complemento', 'bairro', 'cep', 'uf', 'municipio', 'ddd1', 'telefone1', 'ddd2', 'telefone2', 'ddd_fax', 'fax', 'correio_eletronico', 'situacao_especial', 'data_situacao_especial', 'cnpj', 'natureza_juridica_', 'motivo_situacao_cadastral_', 'municipio_', 'cnae_fiscal_', 'pais_']
    #sql = "select * from estabelecimento t left join empresas te on te.cnpj_basico=t.cnpj_basico where t.cnpj=:cnpjin"

    sqlwhere, inLista = sqlWhereF(dados) 

    if not inLista:
        #print('inLista vazio')
        pyout.put_html('<br><br>Digite em algum campo e tente novamente.')
        return "vazio"
    print('sql: ', sql + sqlwhere)
    print(inLista)
    print(time.asctime(), 'Executando sql...')
    pyout.put_html('<br><br>Obtendo os dados. Aguarde ...')
    tsqlInicial = str(time.asctime())
    pyout.put_text(time.asctime(), 'Executando sql - consulta ao banco de dados....')
    engine = sqlite3.connect(caminhoDBReceita)
    with pyout.put_loading():
        with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine:
            df = pd.read_sql(sql + sqlwhere, params=tuple(inLista), con=engine, index_col=None)
            if dados.get('bsocios'):
                listaCNPJs = df['cnpj'].tolist()
                querySocios = sqlSociosF(listaCNPJs)
                print('sql sócios:\n' + querySocios)
                print(listaCNPJs)
                dfsocios = pd.read_sql(querySocios, params=tuple(listaCNPJs), con=engine, index_col=None)
            # print(querySocios)
            # print(inLista)
            # print(dfsocios)
    print(time.asctime(), 'Executando sql -fim.')
    df['cnae_fiscal'] = df['cnae_fiscal'].apply(ajustaCnaes)
    df['cnae_fiscal_secundaria'] = df['cnae_fiscal_secundaria'].apply(ajustaCnaes)
    #df.set_index('cnpj_basico', inplace=True)
    print('Quantidade de registros: ', df.shape[0])

    if df.shape[0]:
        pyout.clear()
        if dados['action']=='consulta':
            pyout.put_html("<b>Dados das empresas - Referência da base de dados: " + data_referencia_base +"</b>")
            pyout.put_text('Parâmetros da consulta: ', parametrosDaConsulta)
            #df.drop(columns=['cnpj_basico', 'cnpj_ordem', 'cnpj_dv'], inplace=True)
            #print(df)
            thtml = ''
            for k in range(df.shape[0]):
                thtml += ''' <div  style="width: 100%;text-align:left;">'''+df.iloc[[k]].T.to_html() +'''</div>''' #+ thtml
            pyout.put_html(thtml)
        
        elif dados['action']=='exporta':
            pyout.put_html("<br><br>")
            pyout.put_text(tsqlInicial, 'Executando sql - consulta ao banco de dados....')
            pyout.put_html(f"<b>O arquivo Excel terá {df.shape[0]} registros.<b>") 
            pyout.put_text(time.asctime(), "Gerando o arquivo no formato Excel...")
            output = io.BytesIO()
            limiteLinhasExcel = 1_000_000 #1048576
            with pyout.put_loading():
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    k = 0
                    pyout.put_text(time.asctime(), "Abas de dados cadastrais...")
                    for start in range(0, df.shape[0], limiteLinhasExcel):
                        df_subset = df.iloc[start:start + limiteLinhasExcel]
                        df_subset.to_excel(writer, startrow = 0, merge_cells = False, sheet_name = f"dados_{k+1}" , index=False, freeze_panes=(1,0))
                        k += 1
                    
                    if dados.get('bsocios'):
                        ks = 0
                        pyout.put_text(time.asctime(), "Abas de dados de sócios...")
                        for start in range(0, dfsocios.shape[0], limiteLinhasExcel):
                            dfsocios_subset = dfsocios.iloc[start:start + limiteLinhasExcel]
                            dfsocios_subset.to_excel(writer, startrow = 0, merge_cells = False, sheet_name = f"socios_{ks+1}" , index=False, freeze_panes=(1,0))
                            ks += 1                        
                        
                    #pyout.put_text('Parâmetros da consulta: ', parametrosDaConsulta)
                    parametrosDaConsulta['Referência Base CNPJ'] = data_referencia_base
                    dfref = pd.DataFrame(list(parametrosDaConsulta.items()), columns=['parâmetro', 'valor'])   
                    dfref.to_excel(writer, startrow = 0, merge_cells = False, sheet_name = "referencia", index=False)
                    dfsobre = pd.DataFrame(['O código fonte do aplicativo está disponível gratuitamente em ', 'https://github.com/rictom/cnpj_consulta'], columns=['Sobre',])
                    dfsobre.to_excel(writer, startrow = 0, merge_cells = False, sheet_name = "Sobre", index=False)
            output.seek(0)
            pyout.put_text(time.asctime(), "Fim do processamento do arquivo no formato Excel!")
            pyout.put_html(" Clique no link para salvar. Se o arquivo for grande, aguarde alguns segundos (não clique diversas vezes no link).")
            pyout.put_file('cnpj_listas.xlsx', output.getvalue(), 'Baixe planilha Excel')
    else:
        if dados['cnpj']:
            pyout.put_text(f"O CNPJ {dados['cnpj']} não foi encontrado na base.")
        else:
            pyout.put_text("Não foram encontrados registros no critério informado.")
        #pyout.put_html(thtml)
    return "executou!"
#.def consulta

def app():
    pywebio.session.set_env(title='CNPJ')
    pyout.clear()

    verificaIndices()
    verificaTabelas()
    while True:
    
        try:
            r = consulta()
            if not r:
                break
            elif r=='limpa':
                continue
        except Exception as e:
            print(str(e))
            try:
                pyout.put_text(str(e))
            except:
                pass
        resposta = pyin.input_group("",[
          pyin.actions('', [ #'texto acima do grupo de botões'
                {'label': 'Nova Consulta', 'value': 'consulta'},
                {'label': 'Sair', 'type': 'cancel', 'value':'sair'},
            ], name='action', help_text='') ]
        )
        if not resposta:
            break
        pyout.clear()    
    #pyout.clear() 
    pyout.put_text('O aplicativo consulta_cnpj foi finalizado.')
    os.kill(os.getpid(), signal.SIGINT) #necessário se foi ativado por pywebio.start_server
    sys.exit()
        
if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
       webbrowser.open('https://www.oarcanjo.net/site/doe/')
    porta = config['ETC'].getint('porta',8011)
    print('o aplicativo pode ser acessado pelo navegador no endereço: ' + f'http://localhost:{porta}')
    webbrowser.open(f'http://localhost:{porta}', new=0, autoraise=True) 
    pywebio.start_server(app, host='0.0.0.0', port=porta)
    #app()
