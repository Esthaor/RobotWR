#!/usr/bin/python

#################################################################################
#																				#
# 				importy bibliotek stosowanych w programie 						#
#																				#
#################################################################################

import sys, argparse, time
from ev3dev import *
from threading import Timer

#################################################################################
#																				#
# 	podlaczenie silnikow i czujnikow robota oraz ustawienie trybow ich pracy	#
#																				#
#################################################################################

lmotor = large_motor(OUTPUT_C); assert lmotor.connected
rmotor = large_motor(OUTPUT_A); assert rmotor.connected
cmotor = medium_motor(OUTPUT_D);assert cmotor.connected
cs     = color_sensor();        assert cs.connected
ls     = light_sensor();        assert ls.connected
ts     = touch_sensor();        assert ts.connected
ir     = infrared_sensor();     assert ir.connected

lmotor.speed_regulation_enabled = 'on'
rmotor.speed_regulation_enabled = 'on'
cmotor.speed_regulation_enabled = 'on'
cs.mode = 'RGB-RAW'
ir.mode = 'IR-PROX'
ls.mode = 'REFLECT'

#################################################################################
#																				#
# 					zmienne i stale uzywane w programie							#
#																				#
#################################################################################

vnorm = 100						# Stala okreslajaca normalna predkosc robota. 
								# Jest to tez predkosc wolnieszego kola.
vmax = 400						# Maksymalna predkosc kola, wartosci powyzej zostaja uciete
speedUpv = 5					# Poczatkowe przyspieszenie szybszego kola
deltav = 1						# Wartosc o jaka zwiekszana jest predkosc szybszego kola co
								# iteracje programu
koloPrzyspieszane = 0			# Flaga okreslajaca przyspieszane kolo:
								# 0 - lewe, 1 - prawe
aktualnePrzyspieszenie = 0		# Aktualna wartosc o ktora szybsze jest kolo przyspieszane
stanLinii = 1 					# Stan line folowera:
								# 0 - pierwszy raz bialy
								# 1 - czarny
								# 2 - drugi raz bialy
blackCounter = 0 				# licznik czarnego koloru wykrytego pod rzad	
szukajBazy = 0					# stan wyszukiwanego koloru zaleznie od aktualnej sytuacji:
								# 0 - szukam zielonego
								# 1 - jade po pilke 
								# 2 - wyjazd z bazy czerwonej z pilka
								# 3 - wyjazd z bazy niebieskiej z pilka
								# 4 - wyjazd z bazy zoltej z pilka
								# 5 - szukam bazy docelowej czerwonej
								# 6 - szukam bazy docelowej niebieskiej
								# 7 - szukam bazy docelowej zoltej
								# 8 - wyjazd z bazy
								# 9 - powrot na trase


#################################################################################
#																				#
# 							funkcje uzywane w programie							#
#																				#
#################################################################################

#
#	Funkcja obslugujaca jazde po linii
#

def lineFollower():
	global vnorm
	global vmax
	global speedUpv
	global deltav
	global koloPrzyspieszane
	global aktualnePrzyspieszenie
	global stanLinii
	global blackCounter
	
	aktualnePrzyspieszenie = deltav + aktualnePrzyspieszenie
	
        if (vnorm + aktualnePrzyspieszenie > vmax):
                aktualnePrzyspieszenie = vmax - vnorm
        if (koloPrzyspieszane == 0):
                lmotor.run_forever(speed_sp=vnorm + aktualnePrzyspieszenie)
                rmotor.run_forever(speed_sp=vnorm - aktualnePrzyspieszenie)
        else:
                lmotor.run_forever(speed_sp=vnorm - aktualnePrzyspieszenie)
                rmotor.run_forever(speed_sp=vnorm + aktualnePrzyspieszenie)
				
        r = cs.value(0)
        g = cs.value(1)
        b = cs.value(2)
		
        if (stanLinii == 0 and r < 60 and g < 85 and b < 55):	# Wykryto czarny kolor i byl w stanie "pierwszego bialego" 
			blackCounter += 1
			aktualnePrzyspieszenie -= (3*deltav)
			if (blackCounter > 3):	# Wykryto czarny kolor w ostatnich 4 odczytach
				stanLinii = 1		# Przejscie do stanu "wykryto czarny"
				blackCounter = 0
        elif (stanLinii == 1 and r > 170 and g > 320  and b > 130):	# Wykryto biały kolor i byl w stanie "wykryto czarny" 
			stanLinii = 2	# Przejscie do stanu "bialy po czarnym", stan w ktorym zmieniamy przyspieszane kolo
        elif (stanLinii == 2 and r > 170 and g > 320 and b > 130):	# Wykryto bialy kolor i byl w stanie "bialy po czarnym"
                stanLinii = 0	# Przejscie do stanu "pierwszy bialy"
        
		if (stanLinii == 2):	# Zmiana kola przyspieszanego w stanie "bialy po czarnym"
                if (koloPrzyspieszane == 0):
                        koloPrzyspieszane = 1
                        aktualnePrzyspieszenie = speedUpv
                else:
                        koloPrzyspieszane = 0
                        aktualnePrzyspieszenie = speedUpv

#
# Funkcja podjazdu do przodu. Argument czas podjazdu.
#

def podjedzDoPrzodu(czas):
	print("Podjezdzam do przodu!")
	
	lmotor.run_forever(speed_sp=50)
	rmotor.run_forever(speed_sp=50)
	
	time.sleep(czas)
	
	lmotor.run_forever(speed_sp=0)
	rmotor.run_forever(speed_sp=0)

#
# Funkcja podjazdu do tylu. Argument czas podjazdu.
#
	
def cofnij(czas):
	print("Cofam!")
	
	lmotor.run_forever(speed_sp=-50)
	rmotor.run_forever(speed_sp=-50)
	
	time.sleep(czas)
	
	lmotor.run_forever(speed_sp=0)
	rmotor.run_forever(speed_sp=0)

#
# Funkcja zawracania.
#

def zawroc():
	print("Zawracam!")
	rmotor.run_forever(speed_sp=150)
	lmotor.run_forever(speed_sp=-150)
	time.sleep(1.4)

#
# Funkcja skretu w prawo lub lewo.
#	
	
def obrocKatProsty(strona):	#-1 lub 1
	print("Skrecam o 90 stopni!")
	rmotor.run_forever(speed_sp=(150*strona))
	lmotor.run_forever(speed_sp=(-150*strona))
	time.sleep(0.6)
	
#
# Funkcja znajdowania koloru.
# Argumentem jest numer koloru:
# 2 - niebieski, 3 - zielony, 4 - zolty, 5 - czerwony
#	

def szukajKoloru(kolor): # 2 - niebieski, 3 - zielony, 4 - zolty, 5 - czerwony
	print("Szukam koloru!")
	
	if (kolor == 2):
		szukaneR = 50
		szukaneG = 140
		szukaneB = 150
	elif (kolor == 3):
		szukaneR = 45
		szukaneG = 194
		szukaneB = 39
	elif (kolor == 4):
		szukaneR = 340
		szukaneG= 380
		szukaneB = 67
	elif (kolor == 5):
		szukaneR = 226
		szukaneG = 79
		szukaneB = 18
	
	znalezione = 0	# flaga czy znaleziono juz kolor
	
	while(znalezione == 0):
		r = cs.value(0)
		g = cs.value(1)
		b = cs.value(2)
		
		if(r > szukaneR - 20 and r < szukaneR + 20 and g > szukaneG - 20 and g < szukaneG + 20 and b > szukaneB - 20 and b < szukaneB + 20):	# warunek znalezienia koloru
			znalezione = 1
	        lmotor.run_forever(speed_sp = 0)
	        rmotor.run_forever(speed_sp = 0)
		else:	# dalsze szukanie koloru
			lmotor.run_forever(speed_sp=-50)
			rmotor.run_forever(speed_sp=50)
		
		time.sleep(0.01)

#
# Funkcja znajdowania czarnej linii. Poszukuje na zasadzie coraz wiekszego wychylania sie na boki az do znalezienia czarnego koloru.
#	
	
def szukajLinii():
	print("Szukam linii!")
	global koloPrzyspieszane
	global aktualnePrzyspieszenie
	global stanLinii
	global blackCounter
	
	wychylenie = 30	# licznik do wychylanej pozycji
	wychylenieStart = 30	# startowa wartosc wychylenia o jaka bedzie sie zwiekszalo wychylenie
	parzystosc = 1	# czy wychylenie jest w lewo czy prawo
	jestLinia = 0	# flaga znalezionej linii
	iterator = 1	# iterator okresla dlugosc wychylenia 

	while (jestLinia == 0):
		if (cs.value(0) > 50 and cs.value(1) > 70 and cs.value(2) > 35 and wychylenie > 0 and parzystosc == 1):
			koloPrzyspieszane = 0
			lmotor.run_forever(speed_sp = 70)
			rmotor.run_forever(speed_sp = -50)
			wychylenie = wychylenie - 1
			if (wychylenie == 0):
				parzystosc = -parzystosc
				wychylenie = iterator * wychylenieStart
				iterator += 1 	
		elif (cs.value(0) > 50 and cs.value(1) > 70 and cs.value(2) > 35 and wychylenie > 0 and parzystosc == -1):
			koloPrzyspieszane = 1
			lmotor.run_forever(speed_sp = -50)
			rmotor.run_forever(speed_sp = 70)
			wychylenie = wychylenie - 1
			if (wychylenie == 0):
				parzystosc = -parzystosc
				wychylenie = iterator * wychylenieStart
				iterator += 1
		else:
			jestLinia = 1
			print("Znalazlem linie!")
		time.sleep(0.01)

	aktualnePrzyspieszenie = 0
	stanLinii = 1
	blackCounter = 10

#
# Funkcja otwierania szczypiec.
#	

def otworzSzczypce():
	print("Otwieram szczypce!")
	cmotor.run_to_abs_pos(speed_sp=100, position_sp = 120)

#
# Funkcja zamykania szczypiec.
#	
	
def zamknijSzczypce():
	print("Zamykam szczypce!")
	cmotor.run_to_abs_pos(speed_sp=100, position_sp = 0)

#################################################################################

#################################################################################
#																				#
# 					Czynnosci przed uruchomieniem robota						#
#																				#
#################################################################################

zamknijSzczypce()				# zamkniecie szczypiec

while not ts.value():	# oczekiwanie na nacisniecie przycisku do startu	
	time.sleep(0.01)
time.sleep(1)

#################################################################################
#																				#
# 							Glowna petla programu								#
#																				#
#################################################################################

while not ts.value():
	
	# Sczytanie kolorow przez czujniki 
	
	r = cs.value(0)
	g = cs.value(1)
	b = cs.value(2)
	
	# jechal po linii, szukal zielonego i znalazl zielony - baze zrodlowa
	if (szukajBazy == 0 and r < 60 and g > 160 and b <80): 	
		print("Znalazlem baze zrodlowa!")
		podjedzDoPrzodu(1.0)
		szukajKoloru(3)
		podjedzDoPrzodu(2.0)
		szukajLinii()
		otworzSzczypce()
		szukajBazy = 1
		
	# jechal po linii, szukal zielonego i znalazl czerwony, niebieski lub żółty - omija
	elif (szukajBazy == 0 and (r > 220 and g < 100 and b < 50) or (r < 60 and g > 130 and b > 140) or (r > 320 and g > 350 and b < 80)):
		print("Omijam baze docelowa bo nie mam pileczki!")
		podjedzDoPrzodu(1.0)
		szukajLinii()
		
	# jechal do bazy po pileczke i natrafil na czerwony, bierze pileczke
	elif (szukajBazy == 1 and r > 220 and g < 100 and b < 50): 
		print("Szukam pileczki - czerwony!")
		while (ir.value() > 11):
			podjedzDoPrzodu(0.1)
		podjedzDoPrzodu(4)
		zamknijSzczypce()
		time.sleep(1)
		zawroc()
		podjedzDoPrzodu(2)
		szukajLinii()
		szukajBazy = 2
		
	# jechal do bazy po pileczke i natrafil na niebieski, bierze pileczke
	elif (szukajBazy == 1 and r < 60 and g > 130 and b > 140): 
		print("Szukam pileczki - niebieski!")
		while (ir.value() > 11):
			podjedzDoPrzodu(0.1)
		podjedzDoPrzodu(4)
		zamknijSzczypce()
		time.sleep(1)
		zawroc()
		podjedzDoPrzodu(2)
		szukajLinii()
		szukajBazy = 3

	# jechal do bazy po pileczke i natrafil na zolty, bierze pileczke
	elif (szukajBazy == 1 and r > 320 and g > 350 and b < 80): 
		print("Szukam pileczki - zolty!")
		while (ir.value() > 11):
			podjedzDoPrzodu(0.1)
		podjedzDoPrzodu(4)
		zamknijSzczypce()
		time.sleep(1)
		zawroc()
		podjedzDoPrzodu(2)
		szukajLinii()
		szukajBazy = 4		
	
	# wyjazd z bazy zrodlowej
	elif ((szukajBazy == 2 or szukajBazy == 3 or szukajBazy == 4) and r < 60 and g > 160 and b < 80): 
		print("Wyjezdzam z bazy zrodlowej!")
		podjedzDoPrzodu(5)
		obrocKatProsty(1)
		szukajLinii()
		szukajBazy += 3
	
	# znalezienie bazy docelowej czerwonej
	elif (szukajBazy == 3 and r > 220 and g < 100 and b < 50): 
		print("Znalazlem baze docelowa!")
		podjedzDoPrzodu(1.0)
		szukajKoloru(5)
		podjedzDoPrzodu(1.0)
		szukajLinii()
		szukajBazy = 8
		
	# znalezienie bazy docelowej niebieskiej
	elif (szukajBazy == 4 and r < 60 and g > 130 and b > 140): 
		print("Znalazlem baze docelowa!")
		podjedzDoPrzodu(1.0)
		szukajKoloru(5)
		podjedzDoPrzodu(1.0)
		szukajLinii()
		szukajBazy = 8
		
	# znalezienie bazy docelowej zoltej
	elif (szukajBazy == 5 and r > 320 and g > 350 and b < 80): 
		print("Znalazlem baze docelowa!")
		podjedzDoPrzodu(1.0)
		szukajKoloru(5)
		podjedzDoPrzodu(1.0)
		szukajLinii()
		szukajBazy = 8
		
	# omijanie bazy zrodlowej jezeli mamy pilke
	elif ((szukajBazy == 3 or szukajBazy == 4 or szukajBazy == 5) and r < 60 and g > 160 and b < 80):
		print("Omijam baze zrodlowa bo mam pileczke!")
		podjedzDoPrzodu(1.0)
		szukajLinii()
	
	# omijanie zlych baz dla czerwonej bazy
	elif (szukajBazy == 3 and ((r < 60 and g > 130 and b > 140) or (r > 320 and g > 350 and b < 80))):
		print("Omijam baze zrodlowa bo mam pileczke!")
		podjedzDoPrzodu(1.0)
		szukajLinii()
		
	# omijanie zlych baz dla niebieskiej bazy
	elif (szukajBazy == 4 and ((r > 220 and g < 100 and b < 50) or (r > 320 and g > 350 and b < 80))):
		print("Omijam baze zrodlowa bo mam pileczke!")
		podjedzDoPrzodu(1.0)
		szukajLinii()
		
	# omijanie zlych baz dla zoltej bazy
	elif (szukajBazy == 5 and ((r > 220 and g < 100 and b < 50) or (r < 60 and g > 130 and b > 140))):
		print("Omijam baze zrodlowa bo mam pileczke!")
		podjedzDoPrzodu(1.0)
		szukajLinii()
		
	# oddanie pileczki do bazy docelowej
	elif (szukajBazy == 8 and((r > 220 and g < 100 and b < 50) or (r < 60 and g > 130 and b > 140) or (r > 320 and g > 350 and b < 80))): 
		print("Zwracam pileczke do bazy docelowej!")
		podjedzDoPrzodu(3)
		otworzSzczypce()
		time.sleep(1)
		cofnij(3.5)
		zamknijSzczypce()
		zawroc()
		cofnij(2)
		szukajLinii()
		szukajBazy = 9
	
	# powrot na trase
	elif (szukajBazy == 9 and((r > 220 and g < 100 and b < 50) or (r < 60 and g > 130 and b > 140) or (r > 320 and g > 350 and b < 80))):
		podjedzDoPrzodu(5)
		obrocKatProsty(1)
		szukajLinii()
		szukajBazy = 0
    
	lineFollower()
	time.sleep(0.001)
