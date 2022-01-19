# -*- coding: utf-8 -*-
"""
Created on Tue Jan 18 00:51:40 2022

@author: rictom
https://github.com/rictom/cnpj_consulta_simples
utiliza a base de cnpjs com dados abertos da Receita, utilizando o script em https://github.com/rictom/cnpj-sqlite
"""
import sqlalchemy, pandas as pd, os, sys

import pywebio 
import pywebio.input as pyin
import pywebio.output as pyout

import nest_asyncio #isso é necessário se for rodar em um ambiente como o spyder
nest_asyncio.apply()

caminhoDBReceita = r"cnpj.db"
if not os.path.exists(caminhoDBReceita):
    print(f'O arquivo {caminhoDBReceita} com a base de cnpjs em sqlite não foi encontrado. O link para o arquivo se encontra em https://github.com/rictom/cnpj-sqlite')
    sys.exit()
engine = sqlalchemy.create_engine(f"sqlite:///{caminhoDBReceita}")

thtml = ''
def consulta():
    global thtml
    def check_form(dados):
        cnpj = dados['cnpj'].replace('.','').replace('/','').replace('-','').strip()
        if len(cnpj)!=14:
            return ('cnpj', 'O campo deve ter 14 dígitos')          
        
    dados = pyin.input_group(
         "Consulta CNPJ",
         [
             pyin.input("Digite um CNPJ", name="cnpj", type=pyin.TEXT, value=''),
             pyin.actions('', [ #'texto acima do grupo de botões'
                 {'label': 'Consultar', 'value': 'consulta'},
                 {'label': 'Limpar', 'type': 'reset'},
                 {'label': 'Sair', 'type': 'cancel'},
             ], name='action', help_text='')
         ],
         validate=check_form
     )
    pyout.put_html(thtml)
    pyout.clear()
    #res = con.execute("select razao_social from estabelecimento t left join empresas te on te.cnpj_basico=t.cnpj_basico where t.cnpj=:cnpjin", {'cnpjin':data['cnpjs']}).fetchone()[0]
    sql = '''
    select te.*, t.*, 
    tnat.descricao as natureza_juridica_, 
    tmot.descricao as motivo_situacao_cadastral_,
    tmun.descricao as municipio_,
    tc.descricao as cnae_fiscal_,
    ifnull(tpa.descricao,'') as pais_
    -- tq.descricao as _qualificacao_responsavel
    from estabelecimento t 
    left join empresas te on te.cnpj_basico=t.cnpj_basico 
    left join natureza_juridica tnat on tnat.codigo=te.natureza_juridica
    left join motivo tmot on tmot.codigo=t.motivo_situacao_cadastral
    left join municipio tmun on tmun.codigo=t.municipio
    left join cnae tc on tc.codigo=t.cnae_fiscal
    left join pais tpa on tpa.codigo=t.pais
    left join qualificacao_socio tq on tq.codigo=te.qualificacao_responsavel
    where t.cnpj=:cnpjin
    '''
    
    #sql = "select * from estabelecimento t left join empresas te on te.cnpj_basico=t.cnpj_basico where t.cnpj=:cnpjin"
    cnpjin = dados['cnpj'].replace('.','').replace('/','').replace('-','').strip()
    df = pd.read_sql(sql, params={'cnpjin':cnpjin}, con=engine, index_col=None)
    df.set_index('cnpj', inplace=True)
    if df.shape[0]:
        pyout.put_html("<b>Dados da empresa:</b>")
        df.drop(columns=['cnpj_basico', 'cnpj_ordem', 'cnpj_dv'], inplace=True)
        #print(df)
        thtml = ''' <div  style="width: 100%;text-align:left;">'''+df.T.to_html()+'''</div>''' + thtml
        pyout.put_html(thtml)
    else:
        pyout.put_text(f"O CNPJ {dados['cnpj']} não foi encontrado na base.")
        pyout.put_html(thtml)

def app():
    pywebio.session.set_env(title='CNPJ')
    pyout.clear()

    while True:
        try:
            consulta()
        except Exception as e:
            print(str(e))
            try:
                pyout.put_text(str(e))
            except:
                pass
        resposta = pyin.input_group("",[
          pyin.actions('', [ #'texto acima do grupo de botões'
                {'label': 'Nova Consulta', 'value': 'consulta'},
                {'label': 'Sair', 'type': 'cancel'},
            ], name='action', help_text='') ]
        )
        pyout.clear()    
        
if __name__ == '__main__':
    import webbrowser
    porta = 8011
    webbrowser.open(f'http://localhost:{porta}', new=0, autoraise=True) 
    pywebio.start_server(app, host='0.0.0.0', port=porta)
