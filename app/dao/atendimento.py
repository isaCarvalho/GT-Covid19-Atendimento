from controller.database import Database
from models.models import Atendimento, AtendimentoInicial, Agendamento, TempoContatoAcompanhamento
from datetime import datetime, timedelta
from models.modelsDomainTable import *
from models.modelsAgendamento import *

from sqlalchemy import desc

class AtendimentoBuilder(): #Incluir funções de cadastro de outras tabelas

    #Classe de atendimento que será moficada aos poucos e salva no fim
    atendimento = None

    #Lista com todas as classes de relacionamento que dependem
    #do id do atendimento para serem salvas.
    relations = []

    #Se não for o atendimento inicial, passa o id do inicial no construtor
    def __init__(self, is_primeiro, data, id_paciente,
                     tentativa=None, id_atendimento_inicial=None, id_inicial=None):
        
        self.atendimento = Atendimento()
        
        self.atendimento.is_primeiro = is_primeiro
        self.atendimento.data = data
        self.atendimento.id_paciente = id_paciente
        self.atendimento.id_atendimento_inicial=id_atendimento_inicial
        self.atendimento.id_inicial = id_inicial

        if tentativa is not None:
            self.atendimento.id_tentativa = self.encontrarIdValor(Tentativa, tentativa)
        else:
            self.atendimento.id_tentativa = None

    #Adiciona uma relação à lista.
    def saveRelation(self, obj):
        self.relations.append(obj)
        
    #Inser uma relação. Adiciona o campo id_atendimento e salva no banco.
    def insertRelation(self, obj, id):
        obj.id_atendimento = id
        db = Database()
        db.saveData(obj)

    #Essa função é utilizada caso o valor de uma tabela de dominio
    #seja passada. Daí, é buscado esse valor no banco. Se não existir,
    #salva. Se existir, recupera o id.
    def encontrarIdValor(self, obj, value):
        db=Database()
        res = db.selectIf(obj, value=value)
        if res is None:
            newObj = obj(value)
            db.saveData(newObj)
            id = db.selectData(newObj)
        else:
            id = res.id
        return id


    #-----------------------------------------------------------------------------
    #Insere os dados do atendimento inicial.
    def inserirAtendimentoInicial(self, endereco, qtd_comodos, is_agua_encanada):
        if(not self.atendimento.is_primeiro): #Caso esse atendimento NAO seja inicial, nao deixa inserir
            return
        inicial = AtendimentoInicial()
        inicial.endereco = endereco
        inicial.qtd_comodos = qtd_comodos
        inicial.is_agua_encanada = is_agua_encanada
        
        db = Database()
        db.saveData(inicial)

        #Recupera o ultimo atendimento inicial salvo para recuperar o ID.
        id = db.Session().query(AtendimentoInicial).order_by(desc(AtendimentoInicial.id)).first().id

        self.atendimento.id_atendimento_inicial = id


    def inserirBeneficioSocial(self, id, outros=None):
        

        self.saveRelation(
            AtendimentoBeneficioSocial(
                id_beneficio_social = id,
                outros_beneficios_sociais = outros
            )
        )
    

    def inserirEstrategiaSaudeFamiliar(self, id, outros=None):
        
        self.saveRelation(
            AtendimentoEstrategiasSaudesFamiliar(
                id_estrategia_saude_familiar = id,
                outras_estrategias_saude_familiar = outros
            )
        )


    def inserirMotivoSair(self, id, outros=None):
        
        
        self.saveRelation(
            AtendimentoMotivoSair(
                id_motivo_sair = id,
                outros_motivos_sair = outros
            )
        )
    

    def adicionarOrientacaoFinal(self, value, comentarios, outros=None):
        
        id = self.encontrarIdValor(OrientacaoFinal, value)
        
        self.saveRelation(
            AtendimentoOrientacaoFinal(
                id_orientacao_final = id,
                comentario = comentarios,
                outras_orientacoes_finais = outros
            )
        )

    #-----------------------------------------------------------------------------
    
    def inserirDoencaCronica(self, doenca=None, medicamento=None, indicador=None,
                        parentesco=None, outros_medicamentos=None,
                        outros_indicadores=None, outras_doencas=None):
        
        self.saveRelation(
            AtendimentoDoecaCronica(
                id_doenca_cronica = doenca,
                id_medicamento = medicamento,
                id_indicador = indicador,
                id_parentesco = parentesco,
                outros_medicamentos = outros_medicamentos,
                outros_indicadores = outros_indicadores,
                outras_doencas_cronicas = outras_doencas
            )
        )
    
    def adicionarSintoma(self, value, medicamento, indicador,
                            parentesco=None, outros_sintomas=None):
        id_sintoma = self.encontrarIdValor(Sintoma, value)
        id_medicamento = self.encontrarIdValor(Medicamento, medicamento)
        id_indicador = self.encontrarIdValor(Indicador, indicador)
        if parentesco is not None:
            id_parentesco = self.encontrarIdValor(Parentesco, parentesco)
        else:
            id_parentesco = None
        
        self.saveRelation(
            AtendimentoSintoma(
                id_sintoma = id_sintoma,
                id_medicamento = id_medicamento,
                id_indicador = id_indicador,
                id_parentesco = id_parentesco,
                outros_sintomas = outros_sintomas
            )
        )
    # --------------------------------------------------------------------

    def finalizarPersistencia(self, id_adm_saude, id_paciente): #Cadastra o atendimento e o agendamento

        db = Database()

        #Finaliza o cadastro do atendimento e recupera o id salvo
        db.saveData(self.atendimento)
        id_atendimento = db.selectIf(Atendimento, id_paciente=self.atendimento.id_paciente,
                                                    data=self.atendimento.data).id

        #Para cada relacionamento salvo, insere o ID do atendimento e cadastra
        for rel in self.relations:
            self.insertRelation(rel, id_atendimento)


        #Cálculo da data do próximo atendimento (agendamento)
        interval = db.selectData(TempoContatoAcompanhamento).intervalo_contato
        data = self.atendimento.data + timedelta(hours=interval)

        #Salva o agendamento
        agendamento = Agendamento()
        agendamento.id_adm_saude = id_adm_saude
        agendamento.id_atendimento = id_atendimento
        agendamento.id_paciente = id_paciente
        agendamento.data = data

        db.saveData(agendamento)
