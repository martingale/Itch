from Itch41 import *
from datetime import datetime
import collections
import time

import numpy as np
import matplotlib.pyplot as plt

class lob(object):
    def __init__(self,ticker, fileName):
        self.fileName =fileName
        self.ob={}
        self.tickerMessages = {}
        self.order_to_time_stamp = {}
        self.seconds = 0
        self.last_ptr = 0
        self.__seconds = 0
        self.id = self.__find_orderbook_id(ticker,fileName)
        self.orderFeatures = self.__process_relevant_messages()


    def find_p_and_q_from_id(self, id, quantity_to_deduce =0):
        time_stamp = self.order_to_time_stamp[id]

        for i, x in enumerate(self.tickerMessages[time_stamp]):
            if x[0] == 'A':
                if x[1] == id:
                    ret_quantity = x[3]

                    if quantity_to_deduce == 0:
                        x[3] = 0
                    else:
                        x[3] -= quantity_to_deduce

                    print("Order in the book:", x, quantity_to_deduce)         #Comment for Jupyter Notebook
                    return ret_quantity, x[5], i # quantity and price
        else:
            return None

        # p_q = [[x[-3], x[-1]] for x in self.tickerMessages[time_stamp] if x[1]==id and x[0]=='A'][0]
        # print(p_q[0]," = ",id)
        # return p_q

    def __find_orderbook_id(self,ticker, fileName):
        cacheSize = 1024 * 1024
        fin = open(fileName, "rb")
        buffer = fin.read(cacheSize)
        # print("buffer:", buffer)
        bufferLen = len(buffer)
        ptr = 0
        haveData = True
        while haveData:
            byte = buffer[ptr:ptr + 1]
            # print(byte)
            ptr += 1
            # print('ptr:', ptr)
            if ptr == bufferLen:
                ptr = 0
                buffer = fin.read(cacheSize)
            bufferLen = len(buffer)
            if len(byte) == 0:
                # print("BREAK-len(byte) == 0")
                break
            if byte == b'\x00':
                length = ord(buffer[ptr:ptr + 1])
                ptr += 1
                if (ptr + length) > bufferLen:
                    temp = buffer[ptr:bufferLen]
                    buffer = temp + fin.read(cacheSize)
                    bufferLen = len(buffer)
                    ptr = 0
                message = buffer[ptr:ptr + length]
                ptr += length
                if chr(message[0]) == 'R':
                    preamble = struct.pack("!h", length)
                    rawMessage = preamble + message
                    itchMessage = ItchMessageFactory.createFromBytes(rawMessage)
                    #print(itchMessage.getValue(Field.OrderBookID))
                    if itchMessage.getValue( Field.Symbol) == ticker:
                        self.last_ptr=ptr
                        return itchMessage.getValue( Field.OrderBookID)
                elif chr(message[0]) == 'A':
                    return None


                if ptr == bufferLen:
                    ptr = 0
                    buffer = fin.read(cacheSize)
                    bufferLen = len(buffer)
        fin.close()


    def __process_relevant_messages(self):
        cacheSize = 1024 * 1024
        fin = open(self.fileName, "rb")

        buffer = fin.read(cacheSize)
        bufferLen = len(buffer)
        ptr = self.last_ptr
        haveData = True
        i=0
        ordFeat = {}
        orders = [[[0 for i in range(10)], [0 for i in range(10)], [0 for i in range(10)]], [[0 for i in range(10)], [0 for i in range(10)], [0 for i in range(10)]]]
        quantityList = [[[0 for i in range(10)], [0 for i in range(10)], [0 for i in range(10)]], [[0 for i in range(10)], [0 for i in range(10)], [0 for i in range(10)]]]
        quantPrice = [[[0 for i in range(10)], [0 for i in range(10)], [0 for i in range(10)]], [[0 for i in range(10)], [0 for i in range(10)], [0 for i in range(10)]]]
        total_price_change = [[0 for i in range(10)], [0 for i in range(10)]]
        midday_del_ord_ids = [[], []]

        i_quantities = [[0 for x in range(67)] for y in range(2)]       # 67 is the maximum i value
        cancel_quantities = [[0 for x in range(67)] for y in range(2)]  # 67 is the maximum i value

        add_ord, del_ord, exe_ord = 0, 1, 2
        buy, sell = 0, 1
        order_start = False
        begin_time = 0
        last_order_book = 0

        while haveData:
            i+=1
            byte = buffer[ptr:ptr + 1]
            ptr += 1
            if ptr == bufferLen:
                ptr = 0
                buffer = fin.read(cacheSize)
            bufferLen = len(buffer)
            if len(byte) == 0:
                # print("BREAK-len(byte) == 0")
                break
            if byte == b'\x00':
                length = ord(buffer[ptr:ptr + 1])
                ptr += 1
                if (ptr + length) > bufferLen:
                    temp = buffer[ptr:bufferLen]
                    buffer = temp + fin.read(cacheSize)
                    bufferLen = len(buffer)
                    ptr = 0
                message = buffer[ptr:ptr + length]
                #ptr += length

                preamble = struct.pack("!h", length)
                rawMessage = preamble + message
                # print("rawMessage :", rawMessage )

                itchMessage = ItchMessageFactory.createFromBytes(rawMessage)
                ptr += length
                # print("itchMessage: ",  itchMessage.getValue( Field.MessageType ) in 'ADC')
                # if fptr(itchMessage):
                #     break
                if itchMessage.getValue(Field.MessageType) =='T':
                    self.__seconds = itchMessage.getValue(Field.Seconds)

                if itchMessage.getValue(Field.OrderBookID) == self.id:
                    if itchMessage.getValue(Field.MessageType) in 'ADE':
                        # print(itchMessage.getValue(Field.MessageType))
                        nanotime = itchMessage.getValue(Field.NanoSeconds)
                        seconds_str = datetime.fromtimestamp(self.__seconds ) # + nanotime/1e9
                        time_stamp = seconds_str.strftime('%Y-%m-%d %H:%M:%S') + '.' + str(int(nanotime % 1000000000)).zfill(9)
                        message_hour = int(seconds_str.strftime('%H'))

                        if not order_start:
                            begin_time = message_hour
                            order_start = True

                        # Get Hour from time_stamp
                        order_id = itchMessage.getValue(Field.OrderID)
                        ob_side = itchMessage.getValue(Field.Side)  # B or S
                        side = sell

                        if ob_side == 'B':
                            side = buy

                        type = itchMessage.getValue(Field.MessageType)
                        self.ob.update({0: time_stamp})
                        # print(ob_side)
                        sign = (int('S' in ob_side) * 2) - 1

                        if type == 'D':
                            this_message = [type, order_id, ob_side]
                            quantity, price, j = self.find_p_and_q_from_id(order_id)
                            #print(price, ':', self.ob[price], ' - ', quantity)
                            if abs(self.ob[price]) < abs(quantity):
                                print("stop deleteden!!")
                                print(price, ':', self.ob[price], ' - ', quantity)
                                break
                            self.ob[price] -= quantity * sign
                                #break

                            if message_hour == 13:
                                midday_del_ord_ids[side].append(order_id)

                            orders[side][del_ord][message_hour - begin_time] += 1
                            quantityList[side][del_ord][message_hour - begin_time] += quantity
                            quantPrice[side][del_ord][message_hour - begin_time] += quantity*price

                            j_value = self.find_i(sorted(self.ob.items()), side, price)
                            before_cancel_quantity = abs(last_order_book[price])

                            if message_hour != 9 and message_hour != 13 and message_hour != 18:
                                cancel_quantities[side][j_value] += (quantity * before_cancel_quantity / 7)

                        elif type == 'A':
                            self.order_to_time_stamp.update({order_id:time_stamp})
                            price = itchMessage.getValue(Field.Price)
                            position = itchMessage.getValue(Field.OrderBookPosition)
                            quantity = itchMessage.getValue(Field.Quantity)
                            this_message = [type, order_id, ob_side, quantity, position, price]
                            i_value = self.find_i(sorted(self.ob.items()), side, price)

                            if message_hour != 9 and message_hour != 13 and message_hour != 18:
                                i_quantities[side][i_value] += (quantity/7)

                            # Quantityler ve Quantity*Pricelar her saat için
                            # Add - delete - execute tahtanin toplam degeri degisimi
                            # Hepsini buy sell sidelarina gore ikili goster

                            if price in self.ob:
                                self.ob[price] += quantity *sign
                            else:
                                self.ob.update({price:quantity*sign })

                            # Add order in add_orders_hourly

                            if message_hour == 14 and (order_id in midday_del_ord_ids[side]):
                                orders[side][del_ord][message_hour - begin_time - 1] -= 1
                                quantityList[side][del_ord][message_hour - begin_time - 1] -= quantity
                                quantPrice[side][del_ord][message_hour - begin_time - 1] -= quantity*price

                            else:
                                orders[side][add_ord][message_hour - begin_time] += 1
                                quantityList[side][add_ord][message_hour - begin_time] += quantity
                                quantPrice[side][add_ord][message_hour - begin_time] += quantity*price

                        elif type == 'E':
                            quantity = itchMessage.getValue(Field.ExecutedQuantity)
                            match_id = itchMessage.getValue(Field.MatchID)
                            this_message = [type, order_id, ob_side, quantity, match_id]
                            q, price, j  = self.find_p_and_q_from_id(order_id, quantity)
                            #print(price,':', self.ob[price],' - ', quantity)
                            if abs(self.ob[price]) < abs(quantity):
                                print("stop execden!!")
                                print(price, ':', self.ob[price], ' - ', quantity)
                                break

                            self.ob[price] -= quantity * sign
                            #self.tickerMessages[]

                            orders[side][exe_ord][message_hour - begin_time] += 1
                            quantityList[side][exe_ord][message_hour - begin_time] += quantity
                            quantPrice[side][exe_ord][message_hour - begin_time] += quantity*price


                        #print(type, ob_side, sign, quantity)


                        if time_stamp not in self.tickerMessages:
                            self.tickerMessages.update( {time_stamp:[this_message]})
                        else:
                            self.tickerMessages.get(time_stamp).append(this_message)

                        last_order_book = collections.OrderedDict(sorted(self.ob.items()))
                        print(collections.OrderedDict(sorted(self.ob.items())))  # Comment for Jupyter Notebook



                if ptr == bufferLen:
                    ptr = 0
                    buffer = fin.read(cacheSize)
                    bufferLen = len(buffer)
            

        ordFeat['executeBuyQuantity'] = quantityList[buy][exe_ord]
        ordFeat['executeSellQuantity'] = quantityList[sell][exe_ord]
        ordFeat['addBuyQuantity'] = quantityList[buy][add_ord]
        ordFeat['addSellQuantity'] = quantityList[sell][add_ord]
        ordFeat['lambdasForLimitBuyOrder'] = i_quantities[buy]
        ordFeat['lambdasForLimitSellOrder'] = i_quantities[sell]
        ordFeat['thetasForBuyCancelOrder'] = cancel_quantities[buy]
        ordFeat['thetasForSellCancelOrder'] = cancel_quantities[sell]

        fin.close()
        return ordFeat

    @staticmethod
    def find_i(items, buy_or_sell, price):

        pa_place = 0
        pb_place = 0
        order_place = 0
        buy, sell = 0, 1

        for i in range(1, len(items)):
            if items[i][1] > 0:
                pa_place = i
                break

        for j in range(pa_place, 0, -1):
            if items[j][1] < 0:
                pb_place = j
                break

        for k in range(1, len(items)):
            if items[k][0] == price:
                order_place = k
                break

        if buy_or_sell == buy:
            return abs(order_place - pa_place)
        else:
            return abs(order_place - pb_place)


