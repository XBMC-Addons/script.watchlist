from time import strptime, mktime
from operator import itemgetter
import itertools
import sys, itertools
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson
import xbmc, xbmcgui, xbmcaddon
# http://mail.python.org/pipermail/python-list/2009-June/596197.html
import _strptime
from threading import Thread

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__cwd__          = __addon__.getAddonInfo('path')

def log(txt):
    message = 'script.watchlist: %s' % txt
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    def __init__( self ):
        self._parse_argv()
        self._init_vars()
        # check how we were executed
        if self.ALBUMID:
            self._play_album( self.ALBUMID )
        else:
            # clear our property, if another instance is already running it should stop now
            self.WINDOW.clearProperty('WatchList_Running')
            self._fetch_info()
            # give a possible other instance some time to notice the empty property
            xbmc.sleep(2000)
            self.WINDOW.setProperty('WatchList_Running', 'True')
            self._daemon()

    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            params = {}
        self.MOVIES = params.get( "movies", "" )
        self.EPISODES = params.get( "episodes", "" )
        self.ALBUMS = params.get( "albums", "" )
        self.LIMIT = int(params.get("limit", "25"))
        self.ALBUMID = params.get( "albumid", "" )

    def _init_vars( self ):
        self.WINDOW = xbmcgui.Window( 10000 )
        self.Player = MyPlayer( action = self._update, movies = ( self.MOVIES == 'true' ), episodes = ( self.EPISODES == 'true' ), albums = ( self.ALBUMS == 'true' ) )

    def _fetch_info( self ):
        if self.MOVIES == 'true':
            self._fetch_movies()
        if self.EPISODES == 'true':
            self._fetch_tvshows()
        if self.ALBUMS == 'true':
            self._fetch_songs()
            self._fetch_albums()
        if self.ALBUMS == 'true':
            self._clear_album_properties()
            self._set_album_properties()

    def _fetch_movies( self ):
        print 'start updating'
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "resume", "genre", "studio", "tagline", "runtime", "fanart", "thumbnail", "file", "plot", "plotoutline", "year", "lastplayed", "rating"], "sort": { "order": "descending", "method": "lastplayed" }, "filter": {"field": "inprogress", "operator": "true", "value": ""}, "limits": {"end": %d}}, "id": 1}' %self.LIMIT)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('movies'):
            count = 0
            self._clear_movie_properties()
            for item in json_response['result']['movies']:
                count += 1
                self.WINDOW.setProperty( "WatchList_Movie.%d.Label" % ( count ), item['title'] )
                self.WINDOW.setProperty( "WatchList_Movie.%d.Year" % ( count ), str(item['year']) )
                self.WINDOW.setProperty( "WatchList_Movie.%d.Genre" % ( count ), " / ".join(item['genre']) )
                self.WINDOW.setProperty( "WatchList_Movie.%d.Studio" % ( count ), item['studio'][0] )
                self.WINDOW.setProperty( "WatchList_Movie.%d.Plot" % ( count ), item['plot'] )
                self.WINDOW.setProperty( "WatchList_Movie.%d.PlotOutline" % ( count ), item['plotoutline'] )
                self.WINDOW.setProperty( "WatchList_Movie.%d.Tagline" % ( count ), item['tagline'] )
                self.WINDOW.setProperty( "WatchList_Movie.%d.Runtime" % ( count ), item['runtime'] )
                self.WINDOW.setProperty( "WatchList_Movie.%d.Fanart" % ( count ), item['fanart'] )
                self.WINDOW.setProperty( "WatchList_Movie.%d.Thumb" % ( count ), item['thumbnail'] )
                self.WINDOW.setProperty( "WatchList_Movie.%d.Path" % ( count ), item['file'] )
                self.WINDOW.setProperty( "WatchList_Movie.%d.Rating" % ( count ), str(round(float(item['rating']),1)) )
        log("movie list: %s items" % len(json_response))
        print 'finished updating'

    def _fetch_tvshows( self ):
        # fetch all episodes in one query
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "studio", "thumbnail", "fanart"], "sort": {"order": "descending", "method": "lastplayed"}, "filter": {"field": "inprogress", "operator": "true", "value": ""}, "limits": {"end": %d}}, "id": 1}'%self.LIMIT)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('tvshows'):
            count = 0
            self._clear_episode_properties()
            for item in json_response['result']['tvshows']:
                count += 1
                print item['title']
                json_query2 = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, "properties": ["title", "playcount", "plot", "season", "episode", "showtitle", "thumbnail", "file", "lastplayed", "rating"], "sort": {"method": "episode"}, "filter": {"field": "playcount", "operator": "is", "value": "0"}, "limits": {"end": 1}}, "id": 1}' %item['tvshowid'] )
                json_query2 = unicode(json_query2, 'utf-8', errors='ignore')
                json_response2 = simplejson.loads(json_query2)
                if json_response2.has_key('result') and json_response2['result'] != None and json_response2['result'].has_key('episodes'):
                    for item2 in json_response2['result']['episodes']:
                        title = item2['title']
                        episode = ("%.2d" % float(item2['episode']))
                        path = item2['file']
                        plot = item2['plot']
                        season = "%.2d" % float(item2['season'])
                        thumbnail = item2['thumbnail']
                        showtitle = item2['showtitle']
                        rating = str(round(float(item2['rating']),1))
                        episodeno = "s%se%s" %(season,episode)
                resumable = "True"
                seasonthumb = ''
                self.WINDOW.setProperty( "WatchList_Episode.%d.Label" % ( count ), title )
                self.WINDOW.setProperty( "WatchList_Episode.%d.Episode" % ( count ), episode )
                self.WINDOW.setProperty( "WatchList_Episode.%d.Season" % ( count ), season )
                self.WINDOW.setProperty( "WatchList_Episode.%d.Plot" % ( count ), plot )
                self.WINDOW.setProperty( "WatchList_Episode.%d.TVShowTitle" % ( count ), showtitle )
                self.WINDOW.setProperty( "WatchList_Episode.%d.Path" % ( count ), path )
                self.WINDOW.setProperty( "WatchList_Episode.%d.Thumb" % ( count ), thumbnail )
                self.WINDOW.setProperty( "WatchList_Episode.%d.Fanart" % ( count ), item['fanart'] )
                self.WINDOW.setProperty( "WatchList_Episode.%d.EpisodeNo" % ( count ), episodeno )
                self.WINDOW.setProperty( "WatchList_Episode.%d.Studio" % ( count ), item['studio'][0] )
                self.WINDOW.setProperty( "WatchList_Episode.%d.TvshowThumb" % ( count ), item['thumbnail'] )
                self.WINDOW.setProperty( "WatchList_Episode.%d.SeasonThumb" % ( count ), seasonthumb )
                self.WINDOW.setProperty( "WatchList_Episode.%d.IsResumable" % ( count ), resumable )
                self.WINDOW.setProperty( "WatchList_Episode.%d.Rating" % ( count ), rating )
        log("tv show list: %s items" % len(json_response))

    def _fetch_seasonthumb( self, tvshowid, seasonnumber ):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["season", "thumbnail"], "tvshowid":%s }, "id": 1}' % tvshowid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('seasons'):
            for item in json_response['result']['seasons']:
                season = "%.2d" % float(item['season'])
                if season == seasonnumber:
                    thumbnail = item['thumbnail']
                    return thumbnail

    def _fetch_songs( self ):
        self.albumsids = {}
        previousid = ''
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["playcount", "albumid"], "sort": { "method": "album" } }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('songs'):
            for item in json_response['result']['songs']:
                albumid = item['albumid']
                if albumid != '':
                    # ignore single tracks that do not belong to an album
                    if albumid != previousid:
                        # new album
                        albumplaycount = 0
                        playcount = item['playcount']
                        albumplaycount = albumplaycount + playcount
                        previousid = albumid
                    else:
                        # song from the same album
                        playcount = item['playcount']
                        albumplaycount = albumplaycount + playcount
                    if playcount != 0:
                        # don't add unplayed items
                        self.albumsids.update({albumid: albumplaycount})
        self.albumsids = sorted(self.albumsids.items(), key=itemgetter(1))
        self.albumsids.reverse()
        log("album list: %s items" % len(self.albumsids))

    def _fetch_albums( self ):
        self.albums = []
        for count, albumid in enumerate( self.albumsids ):
            count += 1
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"properties": ["title", "description", "albumlabel", "artist", "genre", "year", "thumbnail", "fanart", "rating"], "albumid":%s }, "id": 1}' % albumid[0])
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('albumdetails'):
                item = json_response['result']['albumdetails']
                description = item['description']
                album = item['title']
                albumlabel = item['albumlabel']
                artist = item['artist']
                genre = item['genre']
                year = str(item['year'])
                thumbnail = item['thumbnail']
                fanart = item['fanart']
                rating = str(item['rating'])
                if rating == '48':
                    rating = ''
                path = 'XBMC.RunScript(' + __addonid__ + ',albumid=' + str(albumid[0]) + ')'
                self.albums.append((album, artist, genre, year, albumlabel, description, rating, thumbnail, fanart, path))
            if count == int(self.LIMIT):
                # stop here if our list contains more items
                break

    def _play_album( self, ID ):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["file", "fanart"], "albumid":%s }, "id": 1}' % ID)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        # create a playlist
        playlist = xbmc.PlayList(0)
        # clear the playlist
        playlist.clear()
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('songs'):
            for item in json_response['result']['songs']:
                song = item['file']
                fanart = item['fanart']
                # create playlist item
                listitem = xbmcgui.ListItem()
                # add fanart image to the playlist item
                listitem.setProperty( "fanart_image", fanart )
                # add item to the playlist
                playlist.add( url=song, listitem=listitem )
            # play the playlist
            xbmc.Player().play( playlist )

    def _daemon( self ):
        # keep running until xbmc exits or another instance is started
        while (not xbmc.abortRequested) and self.WINDOW.getProperty('WatchList_Running') == 'True':
            xbmc.sleep(500)
        if xbmc.abortRequested:
            log('script stopped: xbmc quit')
        else:
            log('script stopped: new script instance started')

    def _clear_movie_properties( self ):
        for count in range( int(self.LIMIT) ):
            count += 1
            self.WINDOW.clearProperty( "WatchList_Movie.%d.Label" % ( count ) )

    def _clear_episode_properties( self ):
        for count in range( int(self.LIMIT) ):
            count += 1
            self.WINDOW.clearProperty( "WatchList_Episode.%d.Label" % ( count ) )

    def _clear_album_properties( self ):
        for count in range( int(self.LIMIT) ):
            count += 1
            self.WINDOW.clearProperty( "WatchList_Album.%d.Label" % ( count ) )

    def _set_album_properties( self ):
        for count, album in enumerate( self.albums ):
            count += 1
            self.WINDOW.setProperty( "WatchList_Album.%d.Label" % ( count ), album[0] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Artist" % ( count ), " / ".join(album[1]) )
            self.WINDOW.setProperty( "WatchList_Album.%d.Genre" % ( count ), album[2][0] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Year" % ( count ), album[3] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Album_Label" % ( count ), album[4] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Album_Description" % ( count ), album[5] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Rating" % ( count ), album[6] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Thumb" % ( count ), album[7] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Fanart" % ( count ), album[8] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Path" % ( count ), album[9] )
            if count == int(self.LIMIT):
                # stop here if our list contains more items
                break

    def _update( self, type, item, ended ):
        xbmc.sleep(100)
        if type == 'movie':
            self._fetch_movies()
        elif type == 'episode':
            self._fetch_tvshows()
        elif type == 'album':
            xbmc.sleep(1000)
            self._fetch_songs()
            self._fetch_albums()
            self._clear_album_properties()
            self._set_album_properties()

class MyPlayer(xbmc.Player):
    def __init__( self, *args, **kwargs ):
        xbmc.Player.__init__( self )
        self.action = kwargs[ "action" ]
        self.movies = kwargs[ "movies" ]
        self.episodes = kwargs[ "episodes" ]
        self.albums = kwargs[ "albums" ]
        self.substrings = [ '-trailer', 'http://' ]
        self.timer = ""
        self.initValues()

    def onPlayBackStarted( self ):
        xbmc.sleep(5000)
        if type == 'movie':
            self._fetch_movies()
        elif type == 'episode':
            self._fetch_tvshows()
        
    def onPlayBackEnded( self ):
        self.stopTimer()
        if self.type == 'album' and self.albums:
            self.action( 'album', self.item, True )
        if self.type == 'movie':
            self.action( 'movie', self.item, True )
        if self.type == 'episode':
            self.action( 'episode', self.item, True )
        self.initValues()

    def onPlayBackStopped( self ):
        self.stopTimer()
        if self.type == 'album' and self.albums:
            self.action( 'album', self.item, True )
        if self.type == 'movie':
            self.action( 'movie', self.item, ( self.time < 3*60 or self.totalTime * 0.9 <= self.time ) )
        if self.type == 'episode':
            self.action( 'episode', self.item, ( self.totalTime * 0.9 <= self.time ) )
        self.initValues()

    def initValues( self ):
        self.item = []
        self.type = ""
        self.time = 0
        self.totaltime = 0

    def startTimer( self ):
        runtime = 0
        self.shutdown = False
        setTime = False
        while( self.isPlaying() and self.shutdown == False ):
            try:
                runtime = self.getTime()
                setTime = True
            except:
                setTime = False
            if (runtime <= 2):
                xbmc.sleep(3000)
            else:
                xbmc.sleep(1000)
            if setTime:
                self.time = runtime

    def stopTimer( self ):
        if self.timer != "":
            self.shutdown = True
            xbmc.sleep(100)
            if self.timer.isAlive():
                self.timer.join()

if ( __name__ == "__main__" ):
    log('script version %s started' % __addonversion__)
    Main()
