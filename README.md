# cnpj_consulta
Rotina simples em python para consultar cnpj a partir da base de dados públicos da Receita Federal.

Baixe o arquivo cnpj.db em https://www.mediafire.com/folder/1vdqoa2mk0fu9/cnpj-sqlite (base da SRF de 8/1/2022), que é a base de cnpjs em formato SQLITE tratada pelo projeto https://github.com/rictom/cnpj-sqlite.

O arquivo cnpj.db deve estar na mesma pasta que o cnpj_consulta_simples.py. Para executar, digite

python cnpj_consulta_simples.py

O script irá abrir uma janela no navegador padrão:<br>

![consulta_cnpj_01](https://user-images.githubusercontent.com/71139693/150223302-2632a814-3f7c-45f5-b1cf-390d910e24db.jpg)

Digite um cnpj (pode ter pontos ou traços) e clique em Consulta. Vai aparecer o resultado:<br>
![consulta_cnpj_02](https://user-images.githubusercontent.com/71139693/150223321-e139f59f-8058-4388-9605-517d1d970d5c.jpg)

## Pré-requisitos:
Python 3.8;<br>
Bibliotecas pwebio, pandas, sqlalchemy, nest_asyncio e webbrowser.<br>

## Comentários:
Esse projeto é um teste de utilização da biblioteca pywebio (https://pywebio.readthedocs.io/en/latest/), que facilita a construção de uma interface, porque basta codificar tudo em python. A biblioteca gera o html e faz o papel de "servidor" entre o python e o navegador web.<br>

## Outras referências:
Projeto para visualizar os relacionamentos de sócios e de empresas de forma gráfica: https://github.com/rictom/rede-cnpj;<br>
Carregar os dados de cnpjs para o banco de dados MYSQL: https://github.com/rictom/cnpj-mysql.<br>

## Histórico de versões

versão 0.1 (janeiro/2022)
- primeira versão
