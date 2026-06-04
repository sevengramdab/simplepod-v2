#!/usr/bin/env python3
"""
data/phone_simulator/generate_affair.py
======================================
Generates a realistic phone data extraction for Swarm analysis testing.

ELI5: This is like creating a full set of fake blueprints, wire labels,
      and maintenance logs for a training exercise. The new security
      guards need realistic practice material before they handle real
      evidence.

Scenario: Love triangle — Sarah (28, marketing), Marcus (30, coworker),
Derek (32, disabled boyfriend, bitter and controlling).
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

# Seed for reproducible drama
random.seed(42)

DATA_DIR = Path(__file__).parent


def make_timestamp(base: datetime, offset_hours: float) -> str:
    """ELI5: Stamp every log entry with the exact minute it happened."""
    return (base + timedelta(hours=offset_hours)).isoformat()


# =============================================================================
# CHARACTER PROFILES
# =============================================================================

CONTACTS: List[Dict[str, Any]] = [
    {
        "id": "c1",
        "phone_number": "+1-555-0142",
        "name": "Marcus Chen",
        "nickname": "Marcus",
        "relationship": "Coworker",
        "photo": "contacts/marcus.jpg",
        "notes": "Product design lead. Loves hiking. Divorced 2 years ago. Has a golden retriever named Buster.",
        "birthday": "1995-03-18",
        "email": "marcus.chen@novatech.io",
        "social": {"instagram": "@marcus.hikes", "linkedin": "marcuschen-design"},
        "metadata": {
            "last_seen_app": "WhatsApp",
            "read_receipts_enabled": True,
            "typing_indicators": True,
        },
    },
    {
        "id": "c2",
        "phone_number": "+1-555-0199",
        "name": "Derek Holloway",
        "nickname": "Derek 💔",
        "relationship": "Boyfriend",
        "photo": "contacts/derek.jpg",
        "notes": "Former construction foreman. Motorcycle accident, T12 spinal injury, wheelchair bound. Angry at the world. Pain management issues. Hates that Sarah works late.",
        "birthday": "1993-08-04",
        "email": "derek.holloway@gmail.com",
        "social": {"facebook": "derek.holloway.93"},
        "metadata": {
            "last_seen_app": "SMS",
            "read_receipts_enabled": False,
            "typing_indicators": False,
            "blocked_apps": ["Instagram", "Snapchat"],
        },
    },
    {
        "id": "c3",
        "phone_number": "+1-555-0177",
        "name": "Jessica Morales",
        "nickname": "Jess 🤫",
        "relationship": "Best Friend",
        "photo": "contacts/jessica.jpg",
        "notes": "Sarah's ride-or-die since college. Therapist in training. Knows EVERYTHING. Keeps telling Sarah to leave Derek.",
        "birthday": "1996-11-22",
        "email": "jess.morales@therapycollective.org",
        "social": {"instagram": "@jess.therapydaze", "tiktok": "@jesstellsit"},
        "metadata": {
            "last_seen_app": "iMessage",
            "read_receipts_enabled": True,
            "typing_indicators": True,
        },
    },
    {
        "id": "c4",
        "phone_number": "+1-555-0101",
        "name": "Mom",
        "nickname": "Mom ❤️",
        "relationship": "Mother",
        "photo": "contacts/mom.jpg",
        "notes": "Traditional. Thinks Sarah should 'stand by her man.' Prays every night. Sends Bible verses unironically.",
        "birthday": "1968-05-12",
        "email": "patricia.reynolds@yahoo.com",
        "social": {"facebook": "patricia.reynolds.68"},
        "metadata": {
            "last_seen_app": "SMS",
            "read_receipts_enabled": True,
            "typing_indicators": False,
        },
    },
    {
        "id": "c5",
        "phone_number": "+1-555-0163",
        "name": "Amanda from HR",
        "nickname": "Amanda HR",
        "relationship": "HR Representative",
        "photo": "contacts/amanda.jpg",
        "notes": "Has noticed Sarah and Marcus working late. Sent the 'workplace relationships' policy PDF last month.",
        "birthday": "1987-02-14",
        "email": "amanda.patel@novatech.io",
        "metadata": {
            "last_seen_app": "Email",
            "read_receipts_enabled": True,
            "typing_indicators": True,
        },
    },
]

# =============================================================================
# MESSAGE GENERATORS
# =============================================================================

Thread = List[Dict[str, Any]]


def msg(
    sender: str,
    text: str,
    offset: float,
    base: datetime,
    **kwargs: Any,
) -> Dict[str, Any]:
    """ELI5: Write one entry in the communication logbook."""
    return {
        "message_id": f"msg_{random.randint(100000, 999999)}",
        "sender": sender,
        "text": text,
        "timestamp": make_timestamp(base, offset),
        "read": True,
        **kwargs,
    }


def deleted_msg(sender: str, text: str, offset: float, base: datetime) -> Dict[str, Any]:
    """ELI5: A message that was torn out of the logbook but left a ghost imprint."""
    return msg(sender, text, offset, base, deleted=True, deleted_at=make_timestamp(base, offset + 0.1))


def edited_msg(sender: str, original: str, edited: str, offset: float, base: datetime) -> Dict[str, Any]:
    """ELI5: A work order that was crossed out and rewritten."""
    return msg(sender, edited, offset, base, edited=True, original_text=original, edited_at=make_timestamp(base, offset + 0.05))


def reaction_msg(sender: str, text: str, offset: float, base: datetime, reaction: str, reactor: str) -> Dict[str, Any]:
    """ELI5: Someone drew a heart or thumbs-up in the margin of the log."""
    return msg(sender, text, offset, base, reactions=[{"emoji": reaction, "user": reactor, "timestamp": make_timestamp(base, offset + 0.2)}])


# =============================================================================
# THREAD 1: SARAH & MARCUS — The Slow Burn (Weeks 1-9)
# =============================================================================

def build_sarah_marcus_thread() -> Thread:
    """
    ELI5: The secret wire run between two junction boxes that started
          as a low-voltage data line and slowly got upgraded to 240V.
    """
    base = datetime(2026, 3, 2, 9, 0, 0)
    t: Thread = []

    # WEEK 1 — Innocent work banter
    t += [
        msg("Sarah", "Hey! You left your charger in conference room B", 0, base),
        msg("Marcus", "Oh thanks! I was wondering where that went 😅", 0.5, base),
        msg("Sarah", "No worries. Your deck for the quarterly review looked really good btw", 2, base),
        msg("Marcus", "Really? I was up until 2am redoing the user-flow diagrams", 2.3, base),
        msg("Sarah", "It shows. The stakeholder journey map is *chef's kiss*", 2.5, base),
        msg("Marcus", "Haha coming from you that means a lot. You're basically the reason I didn't quit last quarter lol", 3, base),
        msg("Sarah", "Shut uppp 😂 I'm serious though", 3.2, base, reactions=[{"emoji": "😂", "user": "Marcus", "timestamp": make_timestamp(base, 3.3)}]),
    ]

    # WEEK 2 — Staying late, getting personal
    t += [
        msg("Marcus", "You still here? It's 8:30", 48, base),
        msg("Sarah", "Derek's asleep by now anyway. Might as well finish the copy deck", 48.2, base),
        msg("Marcus", "...everything okay at home?", 48.5, base),
        msg("Sarah", "Yeah yeah. Just... you know how it is", 48.8, base),
        msg("Marcus", "I don't, actually. But I have beer in the mini fridge if you want to vent", 49, base),
        msg("Sarah", "You're going to get me fired 😂", 49.3, base),
        msg("Marcus", "HR left at 5. We're safe.", 49.5, base),
        msg("Sarah", "...one beer.", 50, base),
    ]

    # WEEK 3 — The vulnerability
    t += [
        msg("Sarah", "Thanks for listening last night. I don't really have anyone to talk to about... all that", 96, base),
        msg("Marcus", "Anytime. I meant what I said — you deserve someone who sees how hard you work", 96.5, base),
        msg("Sarah", "Derek used to be like that. Before the accident. Now it's like I'm walking on eggshells AND paying all the bills", 97, base),
        msg("Marcus", "That's not a relationship, Sarah. That's a caretaking arrangement.", 97.5, base),
        msg("Sarah", "I know. I KNOW. But I can't just... leave him. He's disabled because of ME.", 98, base),
        msg("Marcus", "Wait what? I thought it was a motorcycle accident?", 98.3, base),
        msg("Sarah", "It was. We were fighting. He left angry. I didn't stop him.", 98.8, base, reactions=[{"emoji": "💔", "user": "Marcus", "timestamp": make_timestamp(base, 99)}]),
        msg("Marcus", "Sarah. That's not your fault.", 99.5, base),
        deleted_msg("Sarah", "I wish I believed that", 100, base),
        msg("Sarah", "Anyway. New topic. Did you see Amanda's email about the offsite?", 100.5, base),
        msg("Marcus", "Yeah. I was thinking... maybe we could share a car?", 101, base),
    ]

    # WEEK 4 — The offsite, lines blur
    t += [
        msg("Marcus", "Your room is 412? I'm 414. This hotel has no idea what they've done 😂", 168, base),
        msg("Sarah", "MARCUS. Behave.", 168.2, base),
        msg("Marcus", "I'm behaving! I'm VERY well behaved. Ask my therapist.", 168.4, base),
        msg("Sarah", "You have a therapist?", 168.6, base),
        msg("Marcus", "Had. After the divorce. She said I have a 'savior complex and boundary issues.' Sounds about right.", 169, base),
        msg("Sarah", "...do I need saving, Marcus?", 170, base),
        msg("Marcus", "You need someone who doesn't make you feel small. That's not saving. That's baseline.", 170.5, base),
        msg("Sarah", "Why are you being so nice to me?", 171, base),
        msg("Marcus", "Because when you laugh at my bad jokes, the whole room gets brighter. And I think you've forgotten that's possible.", 172, base),
        reaction_msg("Sarah", "...", 172.5, base, "❤️", "Marcus"),
        msg("Marcus", "Shit. I'm sorry. That was too much. Forget I said that.", 173, base, edited=True, original_text="Shit. I'm sorry. That was too much. Forget I said that. I know you're with Derek.", edited_at=make_timestamp(base, 173.1)),
        msg("Sarah", "I didn't forget.", 174, base),
    ]

    # WEEK 5 — The guilt spiral
    t += [
        msg("Sarah", "I told Jessica about the offsite", 216, base),
        msg("Marcus", "And?", 216.3, base),
        msg("Sarah", "She said I need to break up with Derek BEFORE anything happens with you. If anything happens.", 216.5, base),
        msg("Marcus", "She's not wrong", 217, base),
        msg("Sarah", "I know. But Derek can't work. He can't drive. His mom blames me already. If I leave... what happens to him?", 217.5, base),
        msg("Marcus", "What happens to YOU if you stay?", 218, base),
        msg("Sarah", "I hate that you ask the hard questions.", 218.5, base),
        msg("Marcus", "I hate that nobody else is asking them.", 219, base),
        msg("Sarah", "I need time. Please. Don't... don't stop being my friend.", 220, base),
        msg("Marcus", "I'm not going anywhere. But I'm also not going to pretend I don't feel this.", 220.5, base),
    ]

    # WEEK 6 — Derek gets suspicious
    t += [
        msg("Derek", "Who's Marcus?", 264, base),
        msg("Sarah", "My coworker? Why?", 264.2, base),
        msg("Derek", "Your phone lit up at 11pm. 'Marcus: I'm not going anywhere.' Real cute.", 264.5, base),
        msg("Sarah", "We were talking about the product launch. He's on my team.", 265, base),
        msg("Derek", "You smell different. New perfume?", 265.5, base),
        msg("Sarah", "It's the sample from Sephora I told you about.", 266, base),
        msg("Derek", "You used to tell me everything. Now I find out about perfume samples from your MOTHER.", 266.5, base),
        msg("Sarah", "Derek, please. I'm exhausted. Can we not do this tonight?", 267, base),
        msg("Derek", "Fine. Go sleep. You look like you need it. Must be hard, all that... teamwork.", 268, base),
        msg("Sarah", "...", 269, base, read=True),
    ]

    # WEEK 7 — Escalation and confession
    t += [
        msg("Sarah", "Derek went through my laptop while I was showering", 312, base),
        msg("Marcus", "What?? Did he find anything?", 312.3, base),
        msg("Sarah", "Our Slack DMs auto-delete but he saw my calendar. 'Dinner with Marcus 8pm' from March 14th.", 312.5, base),
        msg("Marcus", "That was the team dinner! Six people were there!", 313, base),
        msg("Sarah", "I know. He doesn't care. He said 'where there's smoke there's fire' and threw his plate at the wall.", 313.5, base),
        msg("Marcus", "Sarah this is abuse. You know that right?", 314, base),
        msg("Sarah", "He's in pain. The neuropathy is worse this month. His meds got denied again.", 314.5, base),
        msg("Marcus", "That doesn't give him the right to terrorize you.", 315, base),
        msg("Sarah", "He said if I leave he'll tell everyone I caused the accident. He'll post it. He has pictures of the crash scene.", 316, base),
        msg("Marcus", "...", 316.5, base),
        msg("Marcus", "I'm coming over. I'm getting an Uber right now.", 317, base),
        msg("Sarah", "NO. Marcus no. If he sees you...", 317.3, base),
        msg("Marcus", "Then let him see me. I'm done hiding.", 318, base),
        deleted_msg("Sarah", "I wish you were here right now", 318.5, base),
        msg("Sarah", "Please don't. I'll handle it. I always handle it.", 319, base),
    ]

    # WEEK 8 — The secret meeting
    t += [
        msg("Marcus", "I'm in the parking garage. Level P2. Please.", 360, base),
        msg("Sarah", "I can't leave. He's watching the Ring camera.", 360.3, base),
        msg("Marcus", "Then open the window. I just need to see that you're okay.", 360.5, base),
        msg("Sarah", "I'm not okay. I've been crying for three hours and pretending I'm fine.", 361, base),
        msg("Marcus", "Sarah. I love you. I know it's the wrong time and the wrong way but I need you to hear it from someone who means it.", 362, base),
        msg("Sarah", "Don't say that. Don't make this harder.", 363, base),
        msg("Marcus", "I watched you eat vending machine crackers for dinner because you gave Derek your whole paycheck for his new wheelchair cushion. I watched you laugh at his cruel jokes just to keep the peace. I watched you shrink.", 364, base),
        msg("Sarah", "I don't know how to be big again.", 365, base),
        msg("Marcus", "One step at a time. Step one: look out your window.", 366, base),
        msg("Sarah", "...you're holding a sign.", 367, base),
        msg("Marcus", "It says 'You're allowed to be happy.' Did I spell it right?", 367.5, base),
        reaction_msg("Sarah", "You're an idiot.", 368, base, "😭", "Marcus"),
        msg("Marcus", "Your idiot. If you want me.", 369, base),
    ]

    # WEEK 9 — The discovery
    t += [
        msg("Derek", "I saw him.", 408, base),
        msg("Sarah", "Derek it's not—", 408.1, base),
        msg("Derek", "I saw the sign. I saw you at the window. I have VIDEO, Sarah.", 408.3, base),
        msg("Sarah", "He's my friend. He was checking on me.", 408.5, base),
        msg("Derek", "FRIENDS don't hold up LOVE SIGNS at 1am. FRIENDS don't make my girlfriend CRY TEARS OF JOY.", 409, base),
        msg("Sarah", "What do you want me to say?", 410, base),
        msg("Derek", "Say you'll block him. Say you'll quit your job. Say you'll stay home and take care of me like you PROMISED.", 410.5, base),
        msg("Sarah", "I never promised to be your prisoner.", 411, base),
        msg("Derek", "So that's it? Three years and you're leaving me for some desk jockey with a dog?", 412, base),
        msg("Sarah", "I'm not leaving you FOR him. I'm leaving you because I can't breathe anymore.", 413, base),
        msg("Derek", "You'll regret this. I'll make sure everyone knows what you did. Your mom. Your boss. Instagram. EVERYONE.", 414, base),
        msg("Sarah", "...do what you need to do, Derek. I'm done being afraid.", 415, base),
        msg("Derek", "You'll come back. They always come back. When he's bored of you and you're broken and alone. You'll come crawling back.", 416, base, read=False),
    ]

    return sorted(t, key=lambda x: x["timestamp"])


# =============================================================================
# THREAD 2: SARAH & JESSICA — The Confessional
# =============================================================================

def build_sarah_jessica_thread() -> Thread:
    """
    ELI5: The private radio channel between two electricians who've been
          on the same crew for ten years. No jargon, no filters.
    """
    base = datetime(2026, 3, 2, 9, 0, 0)
    t: Thread = []

    t += [
        msg("Sarah", "Girl. Emergency. Can you talk?", 2, base),
        msg("Jessica", "Always. What's up?", 2.1, base),
        msg("Sarah", "I think I have feelings for Marcus.", 2.3, base),
        msg("Jessica", "The cute product guy with the dog? ABOUT TIME", 2.4, base),
        msg("Sarah", "Jess it's not funny!! I'm still with Derek!", 2.5, base),
        msg("Jessica", "Okay okay. Deep breath. Tell me everything. Start from the beginning.", 2.7, base),
    ]

    t += [
        msg("Sarah", "We worked until 10pm last night. He bought me Thai food. We talked about everything.", 50, base),
        msg("Jessica", "Thai food is the gateway drug to emotional affairs", 50.2, base),
        msg("Sarah", "He's just... kind. He asks about my day and actually LISTENS. Derek hasn't asked about my day in two years.", 50.5, base),
        msg("Jessica", "Sarah. Babe. Derek hasn't asked about your day because Derek is a narcissist wrapped in a victim complex.", 51, base),
        msg("Sarah", "He's DISABLED, Jess. He's in constant pain. That changes people.", 51.3, base),
        msg("Jessica", "Pain doesn't make you cruel. Cruel makes you cruel. My clients in wheelchairs are some of the gentlest people I know.", 51.8, base),
        msg("Sarah", "...", 52, base),
        msg("Jessica", "I'm not saying leave him because of Marcus. I'm saying leave him because he makes you smaller. Marcus is just showing you what big feels like.", 53, base),
        reaction_msg("Sarah", "When did you get so wise", 53.5, base, "🥺", "Jessica"),
    ]

    t += [
        msg("Sarah", "The offsite happened.", 175, base),
        msg("Jessica", "AND???", 175.1, base),
        msg("Sarah", "Nothing physical. But... he told me I deserve baseline happiness. And I cried in a hotel bathroom for 20 minutes.", 175.5, base),
        msg("Jessica", "Because it's true?", 176, base),
        msg("Sarah", "Because I don't know if I believe it's true. What if Derek is right and I'm just selfish?", 176.5, base),
        msg("Jessica", "Want me to list the ways you are NOT selfish? You pay his rent. You cook his meals. You tolerate his abuse. You canceled your sister's wedding trip because he had a 'bad day.' You are MARTYRED, not selfish.", 177, base),
        msg("Sarah", "I don't want to be a martyr. I just want to feel like myself again.", 178, base),
        msg("Jessica", "Then take the leap, baby. I'll catch you.", 179, base),
    ]

    t += [
        msg("Sarah", "Derek found out.", 320, base),
        msg("Jessica", "I'm getting in my car.", 320.1, base),
        msg("Sarah", "NO. I'm okay. I mean I'm not okay but I'm safe. He threatened to post about the accident.", 320.3, base),
        msg("Jessica", "That's illegal. Coercion, harassment, defamation. I can call my lawyer friend right now.", 320.5, base),
        msg("Sarah", "I just need to figure out what I want. For the first time in three years.", 321, base),
        msg("Jessica", "What do you want?", 322, base),
        msg("Sarah", "I want to wake up and not feel guilty before my feet hit the floor. I want someone to bring me coffee instead of demanding it. I want to laugh until my face hurts. I want... him. Marcus. Is that terrible?", 323, base),
        msg("Jessica", "No, babe. That's the most human thing you've said in years.", 324, base),
    ]

    return sorted(t, key=lambda x: x["timestamp"])


# =============================================================================
# THREAD 3: SARAH & DEREK — The Decline
# =============================================================================

def build_sarah_derek_thread() -> Thread:
    """
    ELI5: The circuit that used to carry warm light but now only
          delivers brownouts and intermittent faults.
    """
    base = datetime(2026, 3, 2, 9, 0, 0)
    t: Thread = []

    t += [
        msg("Derek", "Where are you", 12, base),
        msg("Sarah", "Still at work. The quarterly report—", 12.1, base),
        msg("Derek", "It's 9pm. Again.", 12.2, base),
        msg("Sarah", "I know. I'm sorry. I'll pick up Thai on the way home.", 12.4, base),
        msg("Derek", "You know I can't eat Thai. The spices mess with my meds.", 12.6, base),
        msg("Sarah", "Right. Subway then?", 12.8, base),
        msg("Derek", "Just come home. I need help with the catheter bag.", 13, base),
        msg("Sarah", "...", 13.2, base, read=False),
    ]

    t += [
        msg("Derek", "You forgot my physical therapy appointment", 100, base),
        msg("Sarah", "I didn't forget. I had the client presentation. I rescheduled it for Thursday.", 100.2, base),
        msg("Derek", "You didn't ASK me. You just decided. Like you decide everything now.", 100.5, base),
        msg("Sarah", "Derek I'm trying to keep us afloat. Your disability check is late and my bonus is covering the mortgage.", 101, base),
        msg("Derek", "Oh so now I'm a BURDEN. Great. Thanks for the reminder.", 101.5, base),
        msg("Sarah", "That's not what I said.", 102, base),
        msg("Derek", "It's what you MEANT. Go back to work. I'll figure it out myself. Like I always do.", 103, base),
        msg("Sarah", "You want me to come home?", 104, base),
        msg("Derek", "Do whatever you want. You always do.", 105, base, read=False),
    ]

    t += [
        msg("Derek", "Your mother called. She thinks we should get married.", 200, base),
        msg("Sarah", "She mentioned it. I told her we're not there yet.", 200.2, base),
        msg("Derek", "Not there yet? It's been THREE YEARS. What's the holdup, Sarah? Is it the chair? Is it because I can't walk down an aisle?", 200.5, base),
        msg("Sarah", "It's because we're not happy, Derek. When did we stop being happy?", 201, base),
        msg("Derek", "When I stopped being USEFUL, apparently. When I became the guy you push around in public and ignore in private.", 201.5, base),
        msg("Sarah", "I don't ignore you. I take care of you every single day.", 202, base),
        msg("Derek", "Taking care isn't the same as loving. Even I know that.", 203, base),
        msg("Sarah", "...", 204, base, read=False),
    ]

    t += [
        msg("Derek", "I found the note. In your coat pocket.", 270, base),
        msg("Sarah", "What note?", 270.2, base),
        msg("Derek", "'You're allowed to be happy.' Nice handwriting. Is that his? Did he WRITE you a LOVE NOTE?", 270.5, base),
        msg("Sarah", "It's not a love note. It's... encouragement.", 271, base),
        msg("Derek", "Encouragement to do WHAT? Leave me? Cheat on me? FUCK some guy who can still feel his legs?", 271.5, base),
        msg("Sarah", "Derek please. You're hurting yourself.", 272, base),
        msg("Derek", "I'm ALREADY hurt! Every day! And you used to care! Now you smell like HIS cologne and smile at your PHONE like I don't EXIST.", 273, base),
        msg("Sarah", "I'm going to stay at Jessica's tonight.", 274, base),
        msg("Derek", "Of course you are. Run to your little friend. Tell her how MEAN the cripple is.", 275, base),
        msg("Sarah", "Don't call yourself that.", 276, base),
        msg("Derek", "Why not? It's what you see. It's what HE sees. A broken man who can't even keep his girlfriend from wandering.", 277, base),
        msg("Sarah", "Goodnight, Derek.", 278, base),
        msg("Derek", "You'll be back. You need me. Nobody else wants damaged goods.", 279, base, read=False),
    ]

    return sorted(t, key=lambda x: x["timestamp"])


# =============================================================================
# THREAD 4: SARAH & MOM — The Generational Divide
# =============================================================================

def build_sarah_mom_thread() -> Thread:
    """
    ELI5: An old two-wire circuit that can't handle the load of
          modern appliances. Every conversation ends in a blown fuse.
    """
    base = datetime(2026, 3, 2, 9, 0, 0)
    t: Thread = []

    t += [
        msg("Mom", "Psalm 31:24 — 'Be strong and take heart, all you who hope in the Lord.' Thinking of you and Derek today ❤️", 24, base),
        msg("Sarah", "Thanks Mom", 24.5, base),
        msg("Mom", "Have you two set a date yet? I'm not getting younger and I want grandchildren while I can still lift them.", 25, base),
        msg("Sarah", "We're not there yet. Things are... complicated.", 25.5, base),
        msg("Mom", "Life is complicated, Sarah. Marriage is complicated. You think your father and I didn't have hard years? But we STAYED. That's what love IS.", 26, base),
        msg("Sarah", "Dad never threw plates at the wall.", 26.5, base),
        msg("Mom", "...what?", 27, base),
        msg("Sarah", "Nothing. I have to go. Meeting.", 27.5, base),
    ]

    t += [
        msg("Mom", "I ran into Mrs. Holloway at the pharmacy. She said Derek has been calling her crying. What's going on?", 220, base),
        msg("Sarah", "I'm thinking about leaving him, Mom.", 220.5, base),
        msg("Mom", "SARAH ELIZABETH REYNOLDS. That man gave up his BODY for you. You cannot abandon him because things got HARD.", 221, base),
        msg("Sarah", "He didn't give up his body FOR me. It was an accident. And he's cruel to me every day.", 221.5, base),
        msg("Mom", "He's in PAIN, baby. Pain makes people say things they don't mean.", 222, base),
        msg("Sarah", "He means them, Mom. He told me nobody else would want me. He threatened to post about the accident. He's not in pain. He's vicious.", 222.5, base),
        msg("Mom", "...you're not seeing clearly. You're tired. Go to church this Sunday. Pray on it.", 223, base),
        msg("Sarah", "I don't need prayer. I need support. Actual support. Not guilt wrapped in Bible verses.", 224, base),
        msg("Mom", "Watch your tone. I am still your mother.", 225, base),
        msg("Sarah", "And I'm still your daughter. But I'm also a PERSON. Goodbye, Mom.", 226, base),
    ]

    return sorted(t, key=lambda x: x["timestamp"])


# =============================================================================
# THREAD 5: MARCUS & JESSICA — The Alliance
# =============================================================================

def build_marcus_jessica_thread() -> Thread:
    """
    ELI5: Two electricians from different crews comparing notes
          on how to safely rewire a dangerous panel.
    """
    base = datetime(2026, 3, 2, 9, 0, 0)
    t: Thread = []

    t += [
        msg("Jessica", "Hey. Sarah's friend. Need to ask you something and I need the truth.", 100, base),
        msg("Marcus", "Jessica, right? Sarah talks about you constantly. What's up?", 100.3, base),
        msg("Jessica", "What are your intentions with her? Because if you're just looking for a work-wife to entertain you between product sprints, I will END you.", 100.5, base),
        msg("Marcus", "Whoa. Okay. Deep breath. I am divorced, in therapy, and absolutely not looking for entertainment. I care about her. A lot.", 101, base),
        msg("Jessica", "She's fragile right now. Derek has worn her down to nothing. If you add to that damage, I swear to god—", 101.5, base),
        msg("Marcus", "I want to BUILD her back up. Not take pieces. I'm not him.", 102, base),
        msg("Jessica", "...okay. You're on probation. But I'm watching.", 103, base),
        msg("Marcus", "Fair. Can I ask you something? How do I help her without making her feel rescued?", 104, base),
        msg("Jessica", "Treat her like she's already whole. She just forgot.", 105, base),
    ]

    t += [
        msg("Marcus", "She's at my place. Derek threatened to post about the accident.", 330, base),
        msg("Jessica", "I'm getting the lawyer. And my cousin who does digital security. If Derek posts anything we nuke it from orbit.", 330.2, base),
        msg("Marcus", "She won't let me call the police. She says he's 'not well.'", 330.5, base),
        msg("Jessica", "He's well enough to manipulate her. She's been gaslit so long she thinks HIS pain is HER fault. Classic trauma bonding.", 331, base),
        msg("Marcus", "How do I get her to see it?", 332, base),
        msg("Jessica", "You can't. She has to see it herself. All you can do is be the safe place she comes back to when she does.", 333, base),
        msg("Marcus", "I'm scared I'll lose her to guilt before she gets there.", 334, base),
        msg("Jessica", "Me too, Marcus. Me too. But for the first time in years, she's CONSIDERING leaving. That's the first domino. Don't knock it over.", 335, base),
    ]

    return sorted(t, key=lambda x: x["timestamp"])


# =============================================================================
# CALL LOGS
# =============================================================================

def build_call_logs() -> List[Dict[str, Any]]:
    """ELI5: The phone company's billing records — who called, how long, incoming or outgoing."""
    base = datetime(2026, 3, 2, 9, 0, 0)
    return [
        {"contact": "Marcus Chen", "number": "+1-555-0142", "direction": "outgoing", "duration_sec": 1847, "timestamp": make_timestamp(base, 52), "status": "completed"},
        {"contact": "Derek Holloway", "number": "+1-555-0199", "direction": "incoming", "duration_sec": 45, "timestamp": make_timestamp(base, 100), "status": "completed"},
        {"contact": "Derek Holloway", "number": "+1-555-0199", "direction": "incoming", "duration_sec": 12, "timestamp": make_timestamp(base, 168), "status": "missed"},
        {"contact": "Jessica Morales", "number": "+1-555-0177", "direction": "outgoing", "duration_sec": 3204, "timestamp": make_timestamp(base, 175), "status": "completed"},
        {"contact": "Marcus Chen", "number": "+1-555-0142", "direction": "outgoing", "duration_sec": 94, "timestamp": make_timestamp(base, 240), "status": "completed"},
        {"contact": "Derek Holloway", "number": "+1-555-0199", "direction": "incoming", "duration_sec": 0, "timestamp": make_timestamp(base, 264), "status": "missed"},
        {"contact": "Derek Holloway", "number": "+1-555-0199", "direction": "incoming", "duration_sec": 0, "timestamp": make_timestamp(base, 264.1), "status": "missed"},
        {"contact": "Derek Holloway", "number": "+1-555-0199", "direction": "incoming", "duration_sec": 0, "timestamp": make_timestamp(base, 264.2), "status": "missed"},
        {"contact": "Marcus Chen", "number": "+1-555-0142", "direction": "outgoing", "duration_sec": 4521, "timestamp": make_timestamp(base, 360), "status": "completed"},
        {"contact": "Jessica Morales", "number": "+1-555-0177", "direction": "outgoing", "duration_sec": 1800, "timestamp": make_timestamp(base, 400), "status": "completed"},
        {"contact": "Derek Holloway", "number": "+1-555-0199", "direction": "incoming", "duration_sec": 0, "timestamp": make_timestamp(base, 408), "status": "rejected"},
    ]


# =============================================================================
# PHOTOS & MEDIA METADATA
# =============================================================================

def build_media() -> List[Dict[str, Any]]:
    """ELI5: The security camera footage — timestamps, locations, what's in the frame."""
    base = datetime(2026, 3, 2, 9, 0, 0)
    return [
        {"filename": "IMG_3042.jpg", "timestamp": make_timestamp(base, 52), "location": "Novatech Office — Conference Room B", "caption": "Marcus's whiteboard sketch of the user journey", "shared_with": ["Marcus"]},
        {"filename": "IMG_3047.jpg", "timestamp": make_timestamp(base, 168.5), "location": "Grand Hotel — Bar", "caption": "Two beers and a napkin with 'You're allowed to be happy' written on it", "shared_with": []},
        {"filename": "IMG_3051.jpg", "timestamp": make_timestamp(base, 175), "location": "Sarah's Apartment — Bathroom mirror", "caption": "Selfie. Eyes puffy from crying. Caption deleted.", "shared_with": []},
        {"filename": "IMG_3058.jpg", "timestamp": make_timestamp(base, 270), "location": "Sarah's Apartment — Bedroom", "caption": "Derek's broken plate on the floor. Unsent.", "shared_with": []},
        {"filename": "VID_112.mp4", "timestamp": make_timestamp(base, 367), "location": "Sarah's Apartment — Window view", "caption": "Marcus in parking garage holding handwritten sign", "duration_sec": 23, "shared_with": []},
        {"filename": "Screenshot_20260309.png", "timestamp": make_timestamp(base, 240), "location": "Phone screenshot", "caption": "Derek's texts: 14 unread, 3 voice memos", "shared_with": ["Jessica"]},
    ]


# =============================================================================
# GPS LOCATIONS (EXTRACTED)
# =============================================================================

def build_locations() -> List[Dict[str, Any]]:
    """ELI5: The GPS tracker in the company van — everywhere it stopped and for how long."""
    base = datetime(2026, 3, 2, 9, 0, 0)
    return [
        {"lat": 40.7128, "lon": -74.0060, "name": "Novatech HQ", "timestamp": make_timestamp(base, 0), "duration_min": 600},
        {"lat": 40.7150, "lon": -74.0080, "name": "Thai Garden Restaurant", "timestamp": make_timestamp(base, 50), "duration_min": 45},
        {"lat": 40.7200, "lon": -74.0100, "name": "Sarah's Apartment", "timestamp": make_timestamp(base, 55), "duration_min": 180},
        {"lat": 40.7580, "lon": -73.9855, "name": "Grand Hotel — Offsite", "timestamp": make_timestamp(base, 168), "duration_min": 2880},
        {"lat": 40.7150, "lon": -74.0080, "name": "Sarah's Apartment", "timestamp": make_timestamp(base, 264), "duration_min": 120},
        {"lat": 40.7205, "lon": -74.0110, "name": "Marcus's Apartment", "timestamp": make_timestamp(base, 360), "duration_min": 180},
        {"lat": 40.7300, "lon": -73.9950, "name": "Jessica's Apartment", "timestamp": make_timestamp(base, 400), "duration_min": 600},
    ]


# =============================================================================
# WRITE EVERYTHING TO DISK
# =============================================================================

def main() -> None:
    """ELI5: Assemble the full evidence binder and lock it in the filing cabinet."""
    threads_dir = DATA_DIR / "threads"
    threads_dir.mkdir(exist_ok=True)

    # Contacts
    with open(DATA_DIR / "contacts.json", "w", encoding="utf-8") as f:
        json.dump({"contacts": CONTACTS, "device_owner": "Sarah Reynolds", "extracted_at": datetime.now().isoformat()}, f, indent=2)

    # Threads
    threads = {
        "sarah_marcus.json": build_sarah_marcus_thread(),
        "sarah_jessica.json": build_sarah_jessica_thread(),
        "sarah_derek.json": build_sarah_derek_thread(),
        "sarah_mom.json": build_sarah_mom_thread(),
        "marcus_jessica.json": build_marcus_jessica_thread(),
    }
    for filename, messages in threads.items():
        with open(threads_dir / filename, "w", encoding="utf-8") as f:
            json.dump({
                "thread_id": filename.replace(".json", ""),
                "participants": list({m["sender"] for m in messages}),
                "message_count": len(messages),
                "first_message": messages[0]["timestamp"] if messages else None,
                "last_message": messages[-1]["timestamp"] if messages else None,
                "messages": messages,
            }, f, indent=2)

    # Call logs
    with open(DATA_DIR / "call_logs.json", "w", encoding="utf-8") as f:
        json.dump({"calls": build_call_logs()}, f, indent=2)

    # Media
    with open(DATA_DIR / "media.json", "w", encoding="utf-8") as f:
        json.dump({"media": build_media()}, f, indent=2)

    # Locations
    with open(DATA_DIR / "locations.json", "w", encoding="utf-8") as f:
        json.dump({"locations": build_locations()}, f, indent=2)

    # Summary
    total_messages = sum(len(t) for t in threads.values())
    print(f"Generated phone extraction for: Sarah Reynolds")
    print(f"  Contacts:     {len(CONTACTS)}")
    print(f"  Threads:      {len(threads)}")
    print(f"  Messages:     {total_messages}")
    print(f"  Call logs:    {len(build_call_logs())}")
    print(f"  Media items:  {len(build_media())}")
    print(f"  Locations:    {len(build_locations())}")
    print(f"  Output dir:   {DATA_DIR}")


if __name__ == "__main__":
    main()
