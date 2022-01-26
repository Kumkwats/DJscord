import discord
import os
from datetime import datetime
from discord.ext import commands
from config import config

categories = {
    'description': {
        'music': 'Commandes liées à l\'écoute musicale',
        'manage': 'Commandes de gestion du bot',
        'fun': 'Commandes liées à l\'amusement'
    },
    'displayName': {
        'music': 'Musique',
        'manage': 'Gestion',
        'fun': 'Fun'
    }
}

commandsList = {
    'description': {
        'music': {
            'play': 'Permet de lire un son insane depuis Youtube/Spotify ou un lien direct',
            'nowplaying': 'Permet de connaître le son en lecture et son avancement',
            'info': 'Affiche les informations sur une musique de la liste d\'attente',
            'queue': 'Affiche la liste d\'attente',
            'move': 'Permet de déplacer une musique dans la liste d\'attente',
            'skip': 'Passe la musique actuelle',
            'remove': 'Supprime une musique de la liste d\'attente',
            'pause': 'Met en pause la lecture',
            'resume': 'Reprend la lecture',
            'repeat': 'Change le mode de répétition',
            'stop': 'Arrête la lecture',
            'leave': 'Arrête la lecture, vide la liste d\'attente et se déconnecte',
            'goto': 'Se déplace à un autre musique de la liste'
        },
        'manage': {
            'set-prefix': 'Défini un nouveau préfixe pour le robot (défaut $) (Seulement disponible aux utilisateurs disposant de la permission "Gérer les messages")',
            'shutdown': 'Éteint le bot (Seulement disponible au ***créateur***)',
            'ping': 'Retourne le ping du bot'
        },
        'fun': {
            'ah': 'quel plaisir'
        }
    },
    'usage': {
        'music': {
            'play': '<lien Youtube / lien http / recherche Youtube>',
            'info': '<position>',
            'move': '<position actuelle> <nouvelle position>',
            'remove': '<position>',
            'repeat': '<mode>\nExemples : none, entry, all, playlist',
            'goto': '<position>'
        },
        'manage': {
            'set-prefix': '"nouveau préfixe"'
        }
    }
}


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get(context, category, command):
        PREFIX = config.getPrefix()
        title = "Commande %s%s" % (PREFIX, command)

        embed = discord.Embed(
            title=title,
            description=commandsList['description'][category][command],
            color=0x565493
        )
        embed.set_author(
            name="Aide",
            icon_url="https://i.imgur.com/C66eNWB.jpg"
        )

        if command in commandsList['usage'][category]:
            embed.add_field(
                name="Utilisation",
                value="%s%s %s" % (PREFIX, command, commandsList['usage'][category][command]),
                inline=False
            )

        last_update = datetime.fromtimestamp(int(os.path.getmtime(os.path.realpath(__file__))))
        embed.set_footer(text="Dernière mise à jour : %s" % last_update)

        return embed

    @commands.command(aliases=['aide', 'h', 'oskour', 'aled'])
    async def help(self, context, query: str = None):
        PREFIX = config.getPrefix()
        embed = discord.Embed(
            color=0x565493
        )
        last_update = datetime.fromtimestamp(int(os.path.getmtime(os.path.realpath(__file__))))
        embed.set_footer(text="Dernière mise à jour : %s" % last_update)

        if query is None:
            for category in categories['description']:
                embed.set_author(
                    name="Aide de %s" % (self.bot.user.display_name),
                    icon_url="https://i.imgur.com/C66eNWB.jpg"
                )
                embed.title = 'Liste des catégories de commandes'
                embed.add_field(
                    name=categories['displayName'][category],
                    value="-> %shelp %s\n%s" % (PREFIX, category, categories['description'][category]),
                    inline=False
                )
        else:
            if query in categories['description']:
                category = query
                embed.set_author(
                    name="Aide de %s" % (categories['displayName'][category]),
                    icon_url="https://i.imgur.com/C66eNWB.jpg"
                )
                embed.title = 'Liste des commandes de %s' % categories['displayName'][category]
                for command in commandsList['description'][category]:
                    if command in commandsList['usage'][category]:
                        embed.add_field(
                            name=PREFIX+command,
                            value=commandsList['description'][category][command],
                            inline=True
                        )
                        embed.add_field(
                            name="Utilisation",
                            value="%s%s %s" % (PREFIX, command, commandsList['usage'][category][command]),
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name=PREFIX+command,
                            value=commandsList['description'][category][command],
                            inline=False
                        )
            else:
                return await context.send("La catégorie %s n'existe pas\n%shelp pour obtenir de l'aide" % (query, PREFIX))

        return await context.send(embed=embed)
