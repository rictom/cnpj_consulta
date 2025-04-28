# Consulta CNPJ Listas
Rotina para gerar listas de cnpjs a partir da base de dados públicos da Receita Federal.

Primeiro gere o arquivo sqlite com a base de cnpjs utilizando o projeto https://github.com/rictom/cnpj-sqlite. O arquivo cnpj.db terá cerca de 35 GB e deve estar na mesma pasta que o cnpj_listas.py. É recomendável criar um ambiente para rodar o projeto, siga as orientações em https://docs.python.org/pt-br/3/library/venv.html

Dentro de um ambiente python, para instalar as bibliotecas utilizadas, rode
pip install -r requirements.txt

Para executar o script para gerar listas, digite

<b>python cnpj_listas.py</b>

A primeira vez que o script for rodado, irá gerar índices no arquivo cnpj.db. Isso poderá levar dezenas de minutos ou horas para execução, dependendo do computador. O arquivo cnpj.db final terá mais de 60GB!

O script irá abrir uma janela no navegador padrão:<br>
![image](https://github.com/user-attachments/assets/c987cc96-dc18-477c-a378-7643f5bb3548)


## Consulta por CNPJ(s)
Digite um cnpj (pode ter pontos ou traços) e clique em Consulta. Vai aparecer o resultado:<br>
![image](https://github.com/user-attachments/assets/f205d77d-5c71-4887-a88c-8156925d6fa2)

Podem ser colocados vários CNPJs separados por espaços ou vírgulas.
## Consulta por parâmetros
Pode-se utilizar a busca por parâmetros, por exemplo, Órgãos Federais em Brasília:
![image](https://github.com/user-attachments/assets/87288a93-e214-4c52-9643-1d4f8ee1680c)

As consultas podem ser feitas por UF, Município, CEP, Natureza Jurídica, CNAE primária ou secundária, Situação Cadastral, Porte da Empresa, Opção Simples, Opção Mei, Data de Início de Atividades e Capital Social.

## Opção Exportar
Pressionando o botão Exportar, vai resultar em:
![image](https://github.com/user-attachments/assets/7d8df782-893f-471d-b2e2-983f0405b31f)

Clicando no link para o arquivo, pode-se salvar o resultado em planiha:
![image](https://github.com/user-attachments/assets/49630740-0202-467e-91c0-b4a73c5db14b)

## Quantidade de registros no resultado
Para definir a quantidade de resultados, digite nos campos "Limite de Registros na Tela" para número de registros se apertar o botão <b>Consultar</b>, ou "Limite de Registros para Exportar para o Excel" quando se apertar o botão <b>Exportar</b>.
![image](https://github.com/user-attachments/assets/4bfb90be-7283-4b9c-b285-eb1479177e75)

Lembre-se que a base tem mais de 60 milhões de empresas, então dependendo dos parâmetros as consultas poderão demorar.

## Pré-requisitos:
Python 3.12;<br>
Bibliotecas pywebio, pandas, sqlalchemy e nest_asyncio.<br>

## Comentários:
Esse projeto é utiliza a biblioteca pywebio (https://pywebio.readthedocs.io/en/latest/), que facilita a construção de uma interface mínima em python.
Em caso de erros, dúvidas ou sugestões, abra uma issue neste repositório.

## Outras referências:
Projeto para visualizar os relacionamentos de sócios e de empresas de forma gráfica: https://github.com/rictom/rede-cnpj;<br>
Carregar os dados de cnpjs para o banco de dados MYSQL: https://github.com/rictom/cnpj-mysql.<br>

## Histórico de versões
versão 0.2 (abril/2025)
- opção para exportar listas

versão 0.1 (janeiro/2022)
- primeira versão
