#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    MAC-PAN: Clon del clasico juego de Pac Man

    Alejandro Santos <alejolp@alejolp.com.ar>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import os, sys, random, time, pygame
from pygame.constants import *

"""

 Cambiar el valor de la variable MODO para:

 0: Usar graficos de 32x32 y pantalla de 640x480

 1: Usar graficos de 16x16 y pantalla de 640x480 con graficos del doble tamaño
    pixelados.

"""

MODO = 0

if MODO == 0:
    W, H = 640, 480
    TILE_SIZE=32
    DOUBLE_SCREEN_SIZE=False
else:
    W, H = 320, 240
    TILE_SIZE=16
    DOUBLE_SCREEN_SIZE=True

NORTH, EAST, SOUTH, WEST = 3, 0, 2, 1
IMPACT_NONE = 0
IMPACT_WALL = 1
IMPACT_ENEMY = 2

DIAMANTE = {K_UP: NORTH, K_RIGHT: EAST, K_DOWN: SOUTH, K_LEFT: WEST}

YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)

def r(a, b):
    """Random entre a y b"""
    return random.randint(a,b)

def colrp(r, p):
    """El punto p esta dentro del rect r."""
    return p[0] >= r.x and p[0] < r.x + r.w and \
        p[1] >= r.y and p[1] < r.y + r.h

def moveto(x, y, d, step=1):
    if d == NORTH:
        y -= step
        if y < 0: y = 0
    elif d == EAST:
        x += step
        if x > W: x = W
    elif d == WEST:
        x -= step
        if x < 0: x = 0
    elif d == SOUTH:
        y += step
        if y > H: y = H
    return x, y

def canturn(p, newd):
    m = p.m
    x, y = moveto(p.rect.x, p.rect.y, newd)
    r2 = pygame.rect.Rect(x, y, TILE_SIZE, TILE_SIZE)

    return not m.wallhit_rect(r2)

#    if r2.collidelist(m.walls) != -1:
#        return False
#    return True

class Timer(object):
    def __init__(self, sps, limit):
        self.delta = 1000./sps/1000
        self.limit = limit

    def start(self):
        self.t_start = time.time()
        self.x = 0

    def hit(self):
        a = time.time()
        t = a - self.t_start
        if t >= self.delta:
            self.t_start = a
            self.x += 1
            if self.x == self.limit:
                self.x = 0

        return self.x

class Label(object):
    def __init__(self, pos):
        self.pos = pos
        self.img = None
        self.text = None
        fontname = pygame.font.get_default_font()
        fontname = pygame.font.match_font('bitstreamverasans')
        self.font = pygame.font.Font(fontname, 12)

    def set_text(self, text):
        self.text = text
        self.img = self.font.render(text, False, WHITE)
        self.rect = self.img.get_rect()
        self.rect.x, self.rect.y = self.pos

    def render(self, screen):
        if self.img is not None:
            screen.blit(self.img, self.rect)

class EventsObserver(object):
    def __init__(self):
        self.events = {}

    def fire_event(self, obj, name):
        w = self.events.get(name, None)
        if w is not None:
            for e in w:
                e(obj, name)

    def register_event(self, name, listener):
        w = self.events.get(name, None)
        if w is None:
            w = self.events[name] = []

        w.append(listener)


class Ent(object):
    """
    Clase jugador
    """
    def __init__(self, m, pos=None):
        self.m = m
        self.still = True
        self.reset()
        if pos is not None:
            self.warppos(pos)
        self.anim = Timer(8, 2)
        self.anim.start()

    def reset(self):
        self.rect = pygame.rect.Rect(W/2, H/2, TILE_SIZE, TILE_SIZE)
        self.d = WEST
        self.points = 0

    def update(self):
        for i in xrange(len(self.m.balls)):
            b = self.m.balls[i]
            if colrp(self.rect, b):
                self.points += 1
                self.m.events.fire_event(self, "ball_destroy")
                del self.m.balls[i]
                break

        x2, y2 = x, y = self.rect.x, self.rect.y

        x, y = moveto(x, y, self.d)

        self.rect.x, self.rect.y = x, y

#        if self.rect.collidelist(self.m.walls) != -1:
        if self.m.wallhit_rect(self.rect):
            self.rect.x, self.rect.y = x2, y2
            x,y=x2,y2

        self.still = ((x, y) == (x2, y2))

    def warppos(self, p):
        self.rect.x, self.rect.y = p

class Enemigo(Ent):
    def __init__(self, m, code, pos, life):
        Ent.__init__(self, m, pos)
        self.code = code
        self.d = r(0, 3)
        self.life = life

    def update(self):
        Ent.update(self)

        if self.still:
            self.d = r(0, 3)

    def impact(self, fx):
        self.life -= 1
        return self.life == 0

class Jugador(Ent):
    def __init__(self, m, pos):
        Ent.__init__(self, m, pos)

    def enemy_collision(self):
        for i in xrange(len(self.m.enemigos)):
            e = self.m.enemigos[i]
            if e.rect.colliderect(self.rect):
                self.m.events.fire_event([self, e], 'player_enemy_collition')
                return True
        return False

class Map(object):
    """
    Clase de mapa del juego
    """
    def __init__(self):
#        self.walls = []
        self.mapmatrix = None
        self.enemigos = []
        self.enemiesstart = []
        self.playerstart = None

        self.events = EventsObserver()

        self.loadmapfile()
        self.fillballs()
        self.loadenemies()

    def loadmapfile(self):
        f = open('media/macpan-map.txt', 'r')
        self.mapmatrix = []

        y = 0
        for line in f:
            line = line.strip('\r\n')
            self.mapmatrix.append([0] * len(line))

            x = 0
            for c in line:
                if c == '#': # Pared
#                    self.walls.append(pygame.rect.Rect(x * TILE_SIZE, 
#                        y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
                    self.mapmatrix[y][x] = 1
                elif c == '.': # Enemigo
                    self.enemiesstart.append((x * TILE_SIZE, y * TILE_SIZE))
                elif c == '$': # Jugador
                    self.playerstart = x, y
                x += 1
            y += 1
        f.close()

    def fillballs(self):
        """
        Crear las pelotitas amarillas.
        """
#        self.balls = [(r(0, W), r(0, H)) for x in xrange(20)]
        self.balls = []

        for x in xrange(50):
            self.balls.append(self.randfreepos())

    def randfreepos(self, tiled=False):
        """
        Devuelve una posicion libre al azar en el mapa, que no haya pared.
        Con el parametro tiled=True devuelve una coordenada valida para ubicar
        enemigos.
        """
        while True:
            if tiled:
                p = r(0, W/TILE_SIZE - 1) * TILE_SIZE, \
                    r(0, H/TILE_SIZE - 1) * TILE_SIZE
            else:
                p = r(0, W - 1), r(0, H - 1)

            x, y = p[0] / TILE_SIZE, p[1] / TILE_SIZE

            if self.mapmatrix[y][x] == 0:
                return p

    def wallhit_rect(self, r):
        # FIXME: Hace falta verificar si r.w | r.h > TILE_SIZE

        points = [(r.x, r.y), (r.x + r.w - 1, r.y), (r.x, r.y + r.h - 1),
            (r.x + r.w - 1, r.y + r.h - 1)]

        for x, y in points:
            x, y = x/TILE_SIZE, y/TILE_SIZE

            if self.mapmatrix[y][x] == 1:
                return True

        return False

    def loadenemies(self):
#        self.enemigos = [Enemigo(self, x % 3, self.randfreepos(True), r(1,2)) for x in xrange(6)]
        self.enemigos = [Enemigo(self, x%3, self.enemiesstart[x], r(1,2))
            for x in xrange(len(self.enemiesstart))]

    def enemydown(self, i):
        del self.enemigos[i]

        newe = Enemigo(self, r(0, 2), self.randfreepos(True), r(1,2))
        self.enemigos.append(newe)

class Fx(object):
    def __init__(self, m, frames, pos, d):
        self.m = m
        self.frames = frames
        self.pos = list(pos)
        self.d = d
        self.anim = Timer(20, 2)
        self.anim.start()

    def update(self):
        x,y = self.pos
        x,y = moveto(x, y, self.d, 3)
        self.pos = [x, y]

    def impact(self):
        """
        Se fija si el Fx colisionó contra algo y devuelve contra qué.
        """
#        if any(colrp(e, self.pos) for e in self.m.walls):
#            return IMPACT_WALL

#        for i in xrange(len(self.m.walls)):
#            e = self.m.walls[i]
#            if colrp(e, self.pos):
#                return IMPACT_WALL

        x, y = self.pos
        if self.m.mapmatrix[y/TILE_SIZE][x/TILE_SIZE] == 1:
            return IMPACT_WALL

        for i in xrange(len(self.m.enemigos)):
            e = self.m.enemigos[i]
            if colrp(e.rect, self.pos):
                if e.impact(self):
                    self.m.enemydown(i)
                return IMPACT_ENEMY

        return IMPACT_NONE
        
    def imgframe(self):
        return self.frames[self.anim.hit()]

class Game(object):
    def __init__(self):
        pass

    def update_title(self):
        self.msg.set_text("MacPan | Vidas: %d | Puntos: %d" % (self.lifes, 
            self.p.points))

    def on_player_enemy_collition(self, obj, name):
        self.lifes -= 1
        self.p.warppos(self.m.randfreepos(True))
        self.update_title()

    def on_ball_destroy(self, obj, name):
        self.update_title()

    def main(self):
        pygame.init()

        flags = pygame.DOUBLEBUF | pygame.HWSURFACE

        if DOUBLE_SCREEN_SIZE:
            screen2 = pygame.display.set_mode((W*2, H*2), flags)
            screen = pygame.surface.Surface((W,H))
            realscreenrect = pygame.rect.Rect(0, 0, W*2, H*2)
        else:
            screen = screen2 = pygame.display.set_mode((W, H), flags)
            realscreenrect = pygame.rect.Rect(0, 0, W, H)

        salir = False
        self.m = m = Map()
        x, y = m.playerstart
        self.p = p = Jugador(m, (x * TILE_SIZE, y * TILE_SIZE))

        self.lifes = 3

        clock = pygame.time.Clock()
        fxs = []

        self.msg = Label((2, 2))
        self.events = self.m.events

        m.events.register_event('ball_destroy',
            self.on_ball_destroy)

        m.events.register_event('player_enemy_collition',
            self.on_player_enemy_collition)

        self.update_title()

        img = pygame.image.load('media/macpan-img-%d.png' % TILE_SIZE)

        # Convierte la imagen al formato de la pantalla y mejora la 
        # performance del juego.
        img = img.convert_alpha()

        imgidx = [(x * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE) for x in xrange(15)]
        trynextturn = None

        tmprect = pygame.rect.Rect(0, 0, TILE_SIZE, TILE_SIZE)

        while not salir:
            # Events
            for e in pygame.event.get():
                if e.type == QUIT:
                    salir = True
                elif e.type == KEYDOWN:
                    if e.key in DIAMANTE.keys():
                        if canturn(p, DIAMANTE[e.key]):
                            p.d = DIAMANTE[e.key]
                            trynextturn = None
                        else:
                            trynextturn = DIAMANTE[e.key]
                    elif e.key == K_SPACE:
                        fxs.append(Fx(m, [13, 14], p.rect.center, p.d))
                    elif e.key == K_ESCAPE:
                        salir = True

            if trynextturn is not None and canturn(p, trynextturn):
                p.d = trynextturn
                trynextturn = None

            # Update
            p.update()
            p.enemy_collision()

            for e in m.enemigos:
                e.update()

            for i in xrange(len(fxs)):
                fxs[i].update()
                ret = fxs[i].impact()
                if ret != IMPACT_NONE:
                    del fxs[i]
                    break

            # Draw
#            pygame.draw.rect(screen, BLACK, screen.get_rect())

            for y in xrange(15):
                for x in xrange(20):
                    tmprect.x = x * TILE_SIZE
                    tmprect.y = y * TILE_SIZE
                    if m.mapmatrix[y][x] == 1:
                        screen.blit(img, tmprect, imgidx[11])
                    else:
                        pygame.draw.rect(screen, BLACK, tmprect)

            for e in m.balls:
                tmprect.center = e
                screen.blit(img, tmprect, imgidx[12])

            for e in m.enemigos:
                screen.blit(img, e.rect, imgidx[8 + e.code])

            for e in fxs:
                tmprect.center = e.pos
                screen.blit(img, tmprect, imgidx[e.imgframe()])

            # Dibujo el Pac Man.
            frame = p.still and (p.d + 4) or (p.d + p.anim.hit() * 4)
            screen.blit(img, p.rect, imgidx[frame])

            self.msg.render(screen)

            # Flip
    #        pygame.transform.scale2x(screen, screen2)
            if DOUBLE_SCREEN_SIZE:
                pygame.transform.scale(screen, (W*2, H*2), screen2)
            pygame.display.flip()

            # Jugar a 45 FPS
            clock.tick(45)

if __name__ == '__main__':
    g = Game()
    g.main()

