def webproxy():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--public-port", type=int, default=7181)
    parser.add_argument("--public-host", default="127.0.0.1")
    parser.add_argument("--private-port", type=int, default=7181)
    parser.add_argument("--private-host", default="127.0.0.1")
    parser.add_argument("--cert", default=None)
    parser.add_argument("allowed_channels", nargs="+")
    args = parser.parse_args()

    if args.public_port == args.private_port and args.public_host == args.private_host:
        print("The given arguments will proxy the server to itself. Aborting.")
        return 1

    import asyncio
    import spoke
    import spoke_web

    proxy = spoke.pubsub.proxy.Server(
        args.allowed_channels,
        conn_client_opts={"port": args.private_port, "host": args.private_host},
        conn_server_class=spoke_web.conn.Server,
        conn_server_opts={
            "port": args.public_port,
            "host": args.public_host,
            "cert": args.cert,
        },
    )

    try:
        asyncio.run(proxy.run())
    except KeyboardInterrupt:
        pass
    return 0
