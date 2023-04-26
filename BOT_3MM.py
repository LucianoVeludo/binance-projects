import pandas as pd
import logging
from binance.client import Client
from binance import AsyncClient, BinanceSocketManager
from binance.enums import *
import asyncio
from chaves import api_key, api_secret

# Indicadores utilizados pelo Robô


def indicadores(candle_Close):
    # Calcula a média móvel exponencial Rapida
    emaFast = pd.Series(candle_Close).ewm(span=6).mean().iloc[-1]
    emaFast = float(emaFast)
    # Calcula a média móvel exponencial Lenta
    emaSlow = pd.Series(candle_Close).ewm(span=12).mean().iloc[-1]
    emaSlow = float(emaSlow)
    # Calcula a média móvel exponencial Tendencia
    emaTend = pd.Series(candle_Close).ewm(span=18).mean().iloc[-1]
    emaTend = float(emaTend)

    return emaFast, emaSlow, emaTend

# Lógica de Compra


def Compra():
    if simulation:
        valor_atual = client.get_ticker(symbol=par_negociado)
        valor_compra = float(valor_atual["lastPrice"])
        compra_taxa = round(valor_compra * 0.00075, 3)
        print("Comprado")
        logging.info(
            f"Compra Realizada - Valor: {valor_compra} - Taxa: {compra_taxa}")
        return valor_compra, compra_taxa
    else:
        order_buy = client.create_test_order(
            symbol=par_negociado,
            side=SIDE_BUY,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=1)
        # price='0.00001')
        print(order_buy)
        logging.info("Compra Realizada")

# Lógica de Venda


def Venda():
    if simulation:
        valor_atual = client.get_ticker(symbol=par_negociado)
        valor_venda = float(valor_atual["lastPrice"])
        venda_taxa = round(valor_venda * 0.00075, 3)
        print("Vendeu")
        logging.info(
            f"Venda Realizada - Valor: {valor_venda} - Taxa: {venda_taxa}")
        return valor_venda, venda_taxa
    else:
        order_sell = client.create_test_order(
            symbol=par_negociado,
            side=SIDE_SELL,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=100)
        # price='0.00001')
        print(order_sell)
        logging.info("Venda Realizada")


def Valor_Cur():
    current_price = client.get_ticker(symbol=par_negociado)
    valor_atualizado = float(current_price["lastPrice"])
    return valor_atualizado

# Websocket para atualização dos dados


async def main():
    qtd_op = 0
    qtd_win = 0
    comprado = False
    RED = "\033[1;31m"
    BLUE = "\033[1;34m"
    CYAN = "\033[1;36m"
    GREEN = "\033[0;32m"
    RESET = "\033[0;0m"
    client = await AsyncClient.create()
    bm = BinanceSocketManager(client)
    ts = bm.kline_socket(par_negociado, interval=KLINE_INTERVAL_1HOUR)
    async with ts as tscm:
        while True:
            res = await tscm.recv()
            # print(res)
            candle = res['k']
            Closes = candle['c']
            # Opened = candle['o']
            # High = candle['h']
            # Low = candle['l']
            # Volume = candle['v']
            Closed_candle = candle['x']

            # Informa o preço atual do Ativo
            Preco_ativo = Valor_Cur()
            print("Preço do Ativo: ", float(Preco_ativo))

            indicador = indicadores(candle_close)
            # Calcula a média móvel exponencial Rapida
            emaF = float(indicador[0])
            print("ema Rápida:     ", round(emaF, 2))
            # Calcula a média móvel exponencial Lenta
            emaS = float(indicador[1])
            print("ema Lenta:      ", round(emaS, 2))
            # Calcula a média móvel exponencial Tendencia
            emaT = float(indicador[2])
            print("ema Tendência:  ", round(emaT, 2))

            # No fechamento do candle atualiza os valores na lista
            if Closed_candle:
                candle_close.append(float(Closes))
                # candle_open.append(float(Opened))
                # candle_high.append(float(High))
                # candle_low.append(float(Low))
                # candle_volume.append(float(Volume))
                candle_close.pop(0)
                # candle_open.pop(0)
                # candle_high.pop(0)
                # candle_low.pop(0)
                # candle_volume.pop(0)

            # Verifica a tendencia do mercado
            if emaT < emaF and emaT < emaS:
                Tendencia = GREEN, "Alta", RESET
            else:
                Tendencia = RED, "Baixa", RESET

            print(f"O mercado está em {Tendencia}")

            # Se a MM rapida for maior que a MM lenta,
            # o mercado em Alta e não existir compra em andamento.
            # Temos uma entrada.

            if emaF > emaS and Tendencia == "Alta" and comprado == False:
                logging.info(
                    "--------- Operacao No.", CYAN, qtd_op, RESET, "----- Par: ", CYAN, par_negociado, RESET, " -----")
                compra = Compra()
                print(compra)
                Valor_compra = compra[0]
                maior_preco = compra[0]
                comprado = True
                qtd_op = qtd_op + 1

            if comprado == True:
                if Preco_ativo >= maior_preco:
                    maior_preco = Preco_ativo
                    Trailling_stop = maior_preco * 0.985
                if Valor_compra <= Trailling_stop:
                    stop = GREEN, "Stop Gain", RESET
                else:
                    stop = RED, "Stop Loss", RESET
                print(f"O {stop} é $ {round(Trailling_stop, 2)}")

                if Preco_ativo <= Trailling_stop or emaF <= emaS:
                    # Venda()
                    venda = Venda()
                    print(venda)
                    Valor_venda = venda[0]
                    # print("Vendido em $ ", Valor_venda)
                    comprado = False
                    LP_value = round(Valor_venda - Valor_compra, 2)
                    LP_net = round(LP_value - compra[1] - venda[1], 2)
                    LP_per = round(((Valor_venda / Valor_compra) - 1) * 100, 2)
                    LP_per_net = round(((LP_net / Valor_compra)) * 100, 2)
                    logging.info(
                        f"Lucro/Prejuizo da Op. (BRUTO): $ {LP_value}")
                    logging.info(f"Lucro/Prejuizo da Op. (BRUTO): {LP_per} %")
                    logging.info(
                        f"Lucro/Prejuizo da Op. (LIQUIDO): $ {LP_net}")
                    logging.info(
                        f"Lucro/Prejuizo da Op. (LIQUIDO): {LP_per_net} %")

                    if LP_value > 0:
                        qtd_win = qtd_win + 1
                        Acerto = round(((qtd_win / qtd_op)) * 100, 2)
                    maior_preco = 0.0

            if qtd_op != 0:
                print("Qtd de Operações: ", qtd_op)
                print(f"Comprado? {comprado}")
                if comprado == True:
                    print(f"Comprado em $ ", BLUE,
                          round(Valor_compra, 2), RESET)

            if qtd_win != 0:
                print(f"Qtd de Op. Vencedoras: {qtd_win}")
                print(f"Percentual de Acerto: {Acerto} %")
            print("_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_")

# Dados para interface pySimpleGUI


def settings(par, API_key, API_secret, Tempo, simulation):
    # Inicializa o cliente da API Binance
    client = Client(API_key, API_secret)

    # Definições
    par_negociado = par
    # Definição do tempo grafico que vai operar
    if Tempo == "1m":
        interval = Client.KLINE_INTERVAL_1MINUTE
    elif Tempo == "5m":
        interval = Client.KLINE_INTERVAL_5MINUTE
    elif Tempo == "15m":
        interval = Client.KLINE_INTERVAL_15MINUTE
    elif Tempo == "30m":
        interval = Client.KLINE_INTERVAL_30MINUTE
    elif Tempo == "1h":
        interval = Client.KLINE_INTERVAL_1HOUR
    elif Tempo == "2h":
        interval = Client.KLINE_INTERVAL_2HOUR

    return par_negociado, Tempo, simulation


if __name__ == '__main__':

    # Inicializa o cliente da API Binance
    client = Client(api_key, api_secret)

    # Configuracao de log
    logging.basicConfig(level=logging.INFO, filename="Bot_3MM.log",
                        format="%(asctime)s - %(levelname)s = %(message)s")
    logging.info("Bot Iniciado - 3MM")

    # configuracoes = settings()

    # Definições
    par_negociado = "ETHUSDT"
    interval = Client.KLINE_INTERVAL_1HOUR

    simulation = True
    candle_open = []
    candle_high = []
    candle_low = []
    candle_close = []
    candle_volume = []

    print("_*_*_*_*_*_Bot 3MM Iniciado_*_*_*_*_*_")
    klines = client.get_historical_klines(
        par_negociado, interval, '1 day ago UTC')
    for candles in range(len(klines)-1):
        candle_open.append(float(klines[candles][1]))
        candle_high.append(float(klines[candles][2]))
        candle_low.append(float(klines[candles][3]))
        # print(candle_low)
        candle_close.append(float(klines[candles][4]))
        # print(candle_close)
        candle_volume.append(float(klines[candles][5]))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
