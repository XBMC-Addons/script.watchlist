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
            self._fetch_episodes()
        if self.ALBUMS == 'true':
            self._fetch_songs()
            self._fetch_albums()
        if self.EPISODES == 'true':
            self._clear_episode_properties()
            self._set_episode_properties()
        if self.ALBUMS == 'true':
            self._clear_album_properties()
            self._set_album_properties()

    def _fetch_movies( self ):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "resume", "genre", "studio", "tagline", "runtime", "fanart", "thumbnail", "file", "plot", "plotoutline", "year", "lastplayed", "rating"], "sort": { "order": "descending", "method": "lastplayed" }, "filter": {"field": "inprogress", "operator": "true", "value": ""}, "limits": {"end": %d}}, "id": 1}' %self.LIMIT)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('movies'):
            count = 0
            total = str(len(json_response))
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

    def _fetch_tvshows( self ):
        self.tvshows = []
        # fetch all episodes in one query
        #json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "studio", "thumbnail", "fanart"], "sort": {"method": "title"}}, "filter": {"field": "inprogress", "operator": "true", "value": ""}, "limits": {"end": %d}}, "id": 1}' %self.LIMIT)
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["title", "playcount", "plot", "season", "episode", "showtitle", "thumbnail", "file", "lastplayed", "rating"], "sort": {"method": "episode"} }, "id": 1}' )
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('episodes'):
            json_response = json_response['result']['episodes']
            # our list is sorted by episode number, secondary we sort by tvshow title (itertools.groupy needs contiguous items) and split it into seperate lists for each tvshow
            episodes = [list(group) for key,group in itertools.groupby(sorted(json_response, key=itemgetter('showtitle')), key=itemgetter('showtitle'))]
        # fetch all tvshows, sorted by title 
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "studio", "thumbnail", "fanart"], "sort": {"method": "title"}}, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if json_response.has_key('result') and json_response['result'].has_key('tvshows'):
            for count, tvshow in enumerate(json_response['result']['tvshows']):
                item = [tvshow['tvshowid'], tvshow['thumbnail'], tvshow['studio'], tvshow['title'], tvshow['fanart'], []]
                for episodelist in episodes:
                    if episodelist[0]['showtitle'] == item[3]:
                        item[5] = episodelist
                        break
                self.tvshows.append(item)
        log("tv show list: %s items" % len(self.tvshows))

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

    def _fetch_episodes( self ):
        self.episodes = []
        for tvshow in self.tvshows:
            lastplayed = ""
            episode_sorter = lambda item: (int(item['season']), int(item['episode']))
            for key, group in itertools.groupby(sorted(tvshow[5], key=episode_sorter), episode_sorter):
                playcount = 0
                for item in sorted(group, key=lambda x: (x['lastplayed'], x['episodeid'])):
                    # sort first by lastplayed, so we're certain to always get the latest played item upon final iteration of the loop. Then sort by episodeid, mainly for the case where lastplayed is empty for all items, and we want the latest episodeid to be the one chosen (higher episodeid equals being added later to xbmc)
                    playcount += int(item['playcount'])
                if playcount != 0:
                    # this episode has been watched, record play date (we need it for sorting the final list) and continue to next episode
                    lastplayed = item['lastplayed']
                    if lastplayed == '':
                        # catch exceptions where the episode has been played, but playdate wasn't stored in the db
                        lastplayed = '0'
                    else:
                        datetime = strptime(lastplayed, "%Y-%m-%d %H:%M:%S")
                        lastplayed = str(mktime(datetime))
                    continue
                else:
                    # this is the first unwatched episode, check if the episode is partially watched
                    playdate = item['lastplayed']
                    if (lastplayed == "") and (playdate == ""):
                        # it's a tv show with 0 watched episodes, continue to the next tv show
                        break
                    else:
                        # this is the episode we need
                        title = item['title']
                        episode = "%.2d" % float(item['episode'])
                        path = item['file']
                        plot = item['plot']
                        season = "%.2d" % float(item['season'])
                        thumbnail = item['thumbnail']
                        showtitle = item['showtitle']
                        rating = str(round(float(item['rating']),1))
                        episodeno = "s%se%s" % ( season,  episode, )
                        if not playdate == '':
                            # if the episode is partially watched, use it's playdate for sorting
                            datetime = strptime(playdate, "%Y-%m-%d %H:%M:%S")
                            lastplayed = str(mktime(datetime))
                            resumable = "True"
                        else:
                            resumable = "False"
                        tvshowid = tvshow[0]
                        showthumb = tvshow[1]
                        studio = tvshow[2]
                        fanart = tvshow[4]
                        seasonthumb = ''
                        self.episodes.append([lastplayed, title, episode, season, plot, showtitle, path, thumbnail, fanart, episodeno, studio, showthumb, seasonthumb, resumable, rating, playcount, tvshowid])
                        # we have found our episode, collected all data, so continue to next tv show
                        break
        self.episodes.sort(reverse=True)
        # only fetch seasonthumbs for items that will actually show up in the skin
        for count, episode in enumerate( self.episodes ):
            count += 1
            tvshowid = episode[16]
            season = episode[3]
            episode[12] = self._fetch_seasonthumb(tvshowid, season)
            if count == int(self.LIMIT):
                # stop here if our list contains more items
                break
        log("episode list: %s items" % len(self.episodes))

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
            xbmc.sleep(1000)
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

    def _set_episode_properties( self ):
        for count, episode in enumerate( self.episodes ):
            count += 1
            self.WINDOW.setProperty( "WatchList_Episode.%d.Label" % ( count ), episode[1] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Episode" % ( count ), episode[2] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Season" % ( count ), episode[3] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Plot" % ( count ), episode[4] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.TVShowTitle" % ( count ), episode[5] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Path" % ( count ), episode[6] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Thumb" % ( count ), episode[7] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Fanart" % ( count ), episode[8] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.EpisodeNo" % ( count ), episode[9] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Studio" % ( count ), episode[10][0] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.TvshowThumb" % ( count ), episode[11] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.SeasonThumb" % ( count ), episode[12] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.IsResumable" % ( count ), episode[13] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Rating" % ( count ), episode[14] )
            if count == int(self.LIMIT):
                # stop here if our list contains more items
                break

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
        if type == 'movie':
            self._fetch_movies()

        elif type == 'episode':
            # Only update if it was a new, unwatched episode
            if item[15] == 0:
                for tvshow in self.tvshows:
                    # If tv show names match, set missing values
                    if tvshow[3] == item[5]:
                        fanart = tvshow[4]
                        item[8] = fanart
                        item[10] = tvshow[2]
                        item[11] = tvshow[1]
                        tvshowid = tvshow[0]
                        item[16] = tvshowid
                        # Delete episode from watch list episodes
                        new = True
                        for count, episode in enumerate( self.episodes ):
                            if episode[5] == item[5]:
                                # record our seasonthumb here since we need it later on
                                seasonthumb = episode[12]
                                item[12] = seasonthumb
                                item[7] = episode[7]
                                del self.episodes[count]
                                new = False
                                break
                        # If the show is marked as watched, check for a new episode to add
                        # else add the episode at the beginning of the list
                        if ended:
                            update = False
                            insert = False
                            for ep in tvshow[5]:
                                seasonnumber = "%.2d" % float(ep['season'])
                                episodenumber = "%.2d" % float(ep['episode'])
                                if ( episodenumber != item[2] or seasonnumber != item[3] ) and ep['playcount'] == 0:
                                    if seasonnumber != item[3]:
                                        # our new episode is from the next season, so fetch seasonthumb
                                        seasonthumb = self._fetch_seasonthumb(tvshowid, seasonnumber)
                                    self.episodes.insert( 0, [ep['lastplayed'], ep['title'], episodenumber, seasonnumber, ep['plot'], ep['showtitle'], ep['file'], ep['thumbnail'], fanart, "s%se%s" % ( seasonnumber,  episodenumber, ), tvshow[2], tvshow[1], seasonthumb, "True", str(round(float(ep['rating']),1)), ep['playcount']] )
                                    insert = True
                                    if update:
                                        break
                                elif episodenumber == item[2] and seasonnumber == item[3]:
                                    ep['playcount'] = 1
                                    update = True
                                    if insert:
                                        break
                        else:
                            # If the episode wasn't in the watch list before, set season and episode thumb
                            if new:
                                for ep in tvshow[5]:
                                    seasonnumber = "%.2d" % float(ep['season'])
                                    episodenumber = "%.2d" % float(ep['episode'])
                                    if episodenumber == item[2] and seasonnumber == item[3]:
                                        item[7] = ep['thumbnail']
                                        item[12] = self._fetch_seasonthumb(tvshowid, seasonnumber)
                                        break
                            self.episodes.insert( 0, item )
                        break
                self._clear_episode_properties()
                self._set_episode_properties()
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
        # Set values based on the file content
        if ( self.isPlayingAudio() ):
            self.setValues( 'album' )   
        else:
            # Stop timer thread on start
            self.stopTimer()
            # Update if an item was played (player is playing a playlist)
            if len(self.item) > 0:
                if self.type == 'movie':
                    self.action( 'movie', self.item, ( self.time < 3*60 or self.totalTime * 0.9 <= self.time ) )
                if self.type == 'episode' and self.episodes:
                    self.action( 'episode', self.item, ( self.totalTime * 0.9 <= self.time ) )
                self.initValues()  
            # Start timer thread
            self.timer = Thread(target=self.startTimer)
            self.timer.start()
            if xbmc.getCondVisibility( 'VideoPlayer.Content(movies)' ):
                filename = ''
                isMovie = True
                try:
                    filename = self.getPlayingFile()
                except:
                    pass
                if filename != '':
                    for string in self.substrings:
                        if string in filename:
                            isMovie = False
                            break
                if isMovie:
                    self.setValues( 'movie' )
            elif xbmc.getCondVisibility( 'VideoPlayer.Content(episodes)' ):
                # Check for tv show title and season to make sure it's really an episode
                if xbmc.getInfoLabel('VideoPlayer.Season') != "" and xbmc.getInfoLabel('VideoPlayer.TVShowTitle') != "":
                    self.setValues( 'episode' )

    def onPlayBackEnded( self ):
        self.stopTimer()
        if self.type == 'album' and self.albums:
            self.action( 'album', self.item, True )
        if self.type == 'movie':
            self.action( 'movie', self.item, True )
        if self.type == 'episode' and self.episodes:
            self.action( 'episode', self.item, True )
        self.initValues()

    def onPlayBackStopped( self ):
        self.stopTimer()
        if self.type == 'album' and self.albums:
            self.action( 'album', self.item, True )
        if self.type == 'movie':
            self.action( 'movie', self.item, ( self.time < 3*60 or self.totalTime * 0.9 <= self.time ) )
        if self.type == 'episode' and self.episodes:
            self.action( 'episode', self.item, ( self.totalTime * 0.9 <= self.time ) )
        self.initValues()

    def setValues( self, type ):
        self.type = type
        self.totalTime = 0
        try:
            self.totalTime = self.getTotalTime()
        except:
            pass
        if type == 'movie':
            title = xbmc.getInfoLabel('VideoPlayer.Title')
            year = xbmc.getInfoLabel('VideoPlayer.Year')
            genre = xbmc.getInfoLabel('VideoPlayer.Genre')
            studio = xbmc.getInfoLabel('VideoPlayer.Studio')
            plot = xbmc.getInfoLabel('VideoPlayer.Plot')
            plotoutline = xbmc.getInfoLabel('VideoPlayer.PlotOutline')
            tagline = xbmc.getInfoLabel('VideoPlayer.TagLine')
            runtime = xbmc.getInfoLabel('VideoPlayer.Duration')
            path = xbmc.getInfoLabel('Player.Filenameandpath')
            rating = str(xbmc.getInfoLabel('VideoPlayer.Rating'))
            self.item = ["", title, year, genre, studio, plot, plotoutline, tagline, runtime, "", "", path, rating]
        elif type == 'episode':
            title = xbmc.getInfoLabel('VideoPlayer.Title')
            episode = "%.2d" % float(xbmc.getInfoLabel('VideoPlayer.Episode'))
            path = xbmc.getInfoLabel('Player.Filenameandpath')
            plot = xbmc.getInfoLabel('VideoPlayer.Plot')
            season = "%.2d" % float(xbmc.getInfoLabel('VideoPlayer.Season'))
            showtitle = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
            rating = str(xbmc.getInfoLabel('VideoPlayer.Rating'))
            episodeno = "s%se%s" % ( season,  episode, )
            studio = xbmc.getInfoLabel('VideoPlayer.Studio')
            playcount = xbmc.getInfoLabel('VideoPlayer.PlayCount')
            if playcount != "":
                playcount = int(playcount)
            else:
                playcount = 0
            self.item = ["", title, episode, season, plot, showtitle, path, "", "", episodeno, "", "", "", "True", rating, playcount, ""]
        elif type == 'album':
            pass

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
                xbmc.sleep(5000)
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
