# Teletun - IP over Telegram

Have you ever wanted to transfer IP traffic over an instant messenger? Wanted to test the capabilities of Telegram?

What do you mean by "no", of course you have! So here you go, take it and *have fun*!

# Install instructions

Install the [telegram-cli](https://github.com/vysheng/tg) package (using snap for example).

Run an instance of telegram-cli using the following line:

```
telegram-cli --json -P 4458
```

(Make sure that `-P` is capital, half an hour of debugging was wasted on that already)

Install dependencies:

```
pip install python-pytun pytg
```

Download the python script. Run the python script. Pray to the gods for mercy.

Note that one has to call it as-is while the other has to pass `--server` to the script. The other client will then be available at `10.8.0.1` or `10.8.0.2` depending on your side.

This also requires root on many platforms, as ridiculous as it sounds. Only tested on Ubuntu.

# Performance

Not that it really matters (you didn't think you're going to use this in anything serious, did you?), but actually, performance is not too bad.

Bandwidth is quite limited of course, but you can get a Ping as low as 100-150 ms. I guess they didn't lie when they called it *Instant* Messenger.

# MIT License

(C) Stefan Reiter 2017

Full license text can be found in the file called LICENSE in this Repositories root.

But please do me the favor and don't ever use this thing. It's quite horrible.
