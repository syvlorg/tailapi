import rich.traceback

rich.traceback.install(show_locals=True)

import oreo

from os import environ
from rich import print
from rich.pretty import pprint
from valiant import ccaller, SuperPath, SH

from .tailnet import Tailnet

try:
    import rich_click as click
except ImportError:
    import click

tailscale_atk = environ.get(
    "TAILSCALE_ATK", SH._run(environ.get("TAILSCALE_ATK_COMMAND", None))
)
default_tailscale_atk = environ.get(
    "DEFAULT_TAILSCALE_ATK", SH._run(environ.get("DEFAULT_TAILSCALE_ATK_COMMAND", None))
)


@click.group(no_args_is_help=True)
@click.option(
    "-a",
    "--atk",
    default=tailscale_atk,
    help="The tailscale access token or api key to be used; defaults to reading the `TAILSCALE_ATK' or `DEFAULT_TAILSCALE_ATK' environment variables.",
    required=not tailscale_atk,
)
@click.option("-A", "--all-fields", is_flag=True)
@click.option(
    "-d",
    "--devices",
    cls=oreo.Option,
    help="The device name or id; input `all' to show all devices, or specify multiple times for multiple devices.",
    multiple=True,
    xor=("keys",),
)
@click.option(
    "-k",
    "--keys",
    cls=oreo.Option,
    help="The key id; input `all' to show all keys, or specify multiple times for multiple keys.",
    multiple=True,
    xor=("devices",),
)
@click.option("-e", "--excluded", multiple=True)
@click.option("-n", "--dry-run", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def main(
    ctx,
    all_fields,
    atk,
    devices,
    keys,
    dry_run,
    verbose,
    excluded,
):
    ctx.ensure_object(dict)
    ctx.obj.tailnet = Tailnet(
        all_fields=all_fields,
        devices=devices,
        dry_run=dry_run,
        excluded=excluded,
        oapi=atk,
        keys=keys,
        verbose=verbose,
    )


@main.command()
@click.argument("options", nargs=-1, required=False)
@click.option("-d", "--devices", is_flag=True)
@click.option("-k", "--keys", is_flag=True)
@click.pass_context
def show(ctx, options, devices, keys):
    """OPTIONS: Print a dictionary of (nested) options for the specified devices or keys."""
    oreo.cprint(
        ctx.obj.tailnet.filterattrs(
            options=options, obj="devices" if devices else "keys" if keys else "all"
        )
    )


@main.command(no_args_is_help=True, name="get")
@click.argument("options", nargs=-1)
@click.pass_context
def _get(ctx, options):
    """OPTIONS: Print a (nested) option for the specified devices or keys."""
    oreo.cprint(next(iter(ctx.obj.tailnet.all.values()))._get(*options))


@main.command()
@click.option("-4", "--ipv4", is_flag=True)
@click.option("-6", "--ipv6", is_flag=True)
@click.option("-f", "--first", is_flag=True)
@click.pass_context
def ip(ctx, ipv4, ipv6, first):
    oreo.cprint(ctx.obj.tailnet.ips(ipv4, ipv6, first))


@main.command(name="filter")
@click.argument("options", nargs=-1, required=False)
@click.option("-t", "--tags", multiple=True)
@click.option("-T", "--excluded-tags", multiple=True)
@click.option("-e", "--ephemeral", is_flag=True)
@click.option("-E", "--not-ephemeral", is_flag=True)
@click.option("-p", "--preauthorized", is_flag=True)
@click.option("-P", "--not-preauthorized", is_flag=True)
@click.option("-r", "--reusable", is_flag=True)
@click.option("-R", "--not-reusable", is_flag=True)
@click.option("-A", "--api-keys", is_flag=True, help="Print the API keys.")
@click.option("-O", "--oauth-keys", is_flag=True, help="Print the OAuth keys.")
@click.option(
    "-a",
    "--and-pt",
    cls=oreo.Option,
    xor=("or-pt",),
    is_flag=True,
    help="If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,\nthis flag selects devices or keys with all of the specified tags and properties.\nNote that properties don't work with devices. This is the default.",
)
@click.option(
    "-o",
    "--or-pt",
    cls=oreo.Option,
    xor=("and-pt",),
    is_flag=True,
    help="If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,\nthis flag selects devices or keys with any of the specified tags and properties. Note that properties don't work with devices.",
)
@click.option(
    "-g",
    "--groups",
    multiple=True,
    help="Strings of properties and tags following boolean logic (`&&', `&', or `and', and `||', `|', or `or'),\nsuch as `(ephemeral or reusable) and (tag:server or tag:relay)' deleting all keys with the ephemeral or reusable properties,\nand with the server or relay tags.\nCan be specified multiple times, where `--or-pt' and `--and-pt' will be used to dictate the interactions between groups,\nand can be used with other property and tag options, such as `--ephemeral', etc.\nNegation can be achieved with `!' prefixed to the properties or tags, such as `!ephemeral' or `!tag:server'. Note that properties don't work with devices.",
)
@click.pass_context
def _filter(
    ctx,
    api_keys,
    oauth_keys,
    and_pt,
    or_pt,
    tags,
    excluded_tags,
    ephemeral,
    not_ephemeral,
    preauthorized,
    not_preauthorized,
    reusable,
    not_reusable,
    groups,
    options,
):
    """OPTIONS: Print a dictionary of (nested) options for the filtered devices or keys."""
    oreo.cprint(
        ctx.obj.tailnet.filter(
            options=options,
            convert=False,
            api_keys=api_keys,
            oauth_keys=oauth_keys,
            or_pt=or_pt,
            tags=tags,
            excluded_tags=excluded_tags,
            ephemeral=ephemeral,
            not_ephemeral=not_ephemeral,
            preauthorized=preauthorized,
            not_preauthorized=not_preauthorized,
            reusable=reusable,
            not_reusable=not_reusable,
            groups=groups,
        )
    )


@main.command()
@click.option("--do-not-prompt", is_flag=True)
@click.option("-A", "--all", is_flag=True)
@click.option(
    "-a",
    "--and-pt",
    cls=oreo.Option,
    xor=("or-pt",),
    is_flag=True,
    help="If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,\nthis flag deletes devices or keys with all of the specified tags and properties.\nNote that properties don't work with devices. This is the default.",
)
@click.option("-d", "--devices", is_flag=True)
@click.option("-e", "--ephemeral", is_flag=True)
@click.option("-E", "--not-ephemeral", is_flag=True)
@click.option(
    "-g",
    "--groups",
    multiple=True,
    help="Strings of properties and tags following boolean logic (`&&', `&', or `and', and `||', `|', and `or'),\nsuch as `(ephemeral or reusable) and (tag:server or tag:relay)' deleting all keys with the ephemeral or reusable properties,\nand with the server or relay tags.\nCan be specified multiple times, where `--or-pt' and `--and-pt' will be used to dictate the interactions between groups,\nand can be used with other property and tag options, such as `--ephemeral', etc.\nNegation can be achieved with `!' prefixed to the properties or tags, such as `!ephemeral' or `!tag:server'. Note that properties don't work with devices.",
)
@click.option("-i", "--ignore-error", is_flag=True)
@click.option("-k", "--keys", is_flag=True)
@click.option(
    "-o",
    "--or-pt",
    cls=oreo.Option,
    xor=("and-pt",),
    is_flag=True,
    help="If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,\nthis flag deletes devices or keys with any of the specified tags and properties. Note that properties don't work with devices.",
)
@click.option("-P", "--not-preauthorized", is_flag=True)
@click.option("-p", "--preauthorized", is_flag=True)
@click.option("-R", "--not-reusable", is_flag=True)
@click.option("-r", "--reusable", is_flag=True)
@click.option("-T", "--excluded-tags", multiple=True)
@click.option("-t", "--tags", multiple=True)
@click.pass_context
def delete(
    ctx,
    all,
    and_pt,
    devices,
    do_not_prompt,
    ephemeral,
    excluded_tags,
    groups,
    keys,
    not_ephemeral,
    not_preauthorized,
    not_reusable,
    or_pt,
    preauthorized,
    reusable,
    tags,
):
    ctx.obj.tailnet.delete(
        id="all" if all else "devices" if devices else "keys",
        do_not_prompt=do_not_prompt,
        or_pt=or_pt,
        tags=tags,
        excluded_tags=excluded_tags,
        ephemeral=ephemeral,
        not_ephemeral=not_ephemeral,
        preauthorized=preauthorized,
        not_preauthorized=not_preauthorized,
        reusable=reusable,
        not_reusable=not_reusable,
        groups=groups,
    )


@main.command(no_args_is_help=True)
@click.argument("tags", nargs=-1, required=False)
@click.option("-e", "--ephemeral", is_flag=True)
@click.option("-p", "--preauthorized", is_flag=True)
@click.option("-r", "--reusable", is_flag=True)
@click.option("-j", "--just-key", is_flag=True, help="Just print the key.")
@click.option(
    "-c",
    "--count",
    callback=ccaller(oreo.Counter),
    cls=oreo.Option,
    xor=("groups",),
    default=1,
    help="Number of keys to create.",
)
@click.option(
    "-g",
    "--groups",
    cls=oreo.Option,
    xor=("count",),
    multiple=True,
    help="Strings of properties and tags,\nsuch as `ephemeral reusable tag:relay tag:server' creating an ephemeral and reusable key with tags `relay' and `server'.\nIf used with other property options, such as `--preauthorized', or tag arguments, all keys will have those properties and tags as well.\nNote that tags here must be prefixed with `tag:'.",
)
@click.pass_context
def create(ctx, tags, ephemeral, preauthorized, reusable, just_key, count, groups):
    """TAGS: Note that tags here do not need to be prefixed with `tag:'."""
    tags = set(tags)
    if groups:
        for group in groups:
            split_group = group.split()
            response = ctx.obj.tailnet.create_key(
                ephemeral="ephemeral" in split_group or ephemeral,
                preauthorized="preauthorized" in split_group or preauthorized,
                reusable="reusable" in split_group or reusable,
                tags={tag for tag in split_group if tag.startswith("tag:")} | tags,
            )
            oreo.cprint(response.key if just_key else response)
    else:
        while count:
            response = ctx.obj.tailnet.create_key(
                ephemeral=ephemeral,
                preauthorized=preauthorized,
                reusable=reusable,
                tags=tags,
            )
            oreo.cprint(response.key if just_key else response)


@main.command()
@click.option("-s", "--show", is_flag=True)
@click.option("-e", "--edit", is_flag=True)
@click.option("-E", "--editor", callback=ccaller(SuperPath))
@click.option("-v", "--environment-variables", multiple=True, type=(str, str))
@click.pass_context
def policy(ctx, edit, editor, environment_variables, show):
    if edit or editor:
        with ctx.obj.tailnet.policy._edit() as f:
            click.edit(
                filename=f,
                extension=f.suffix,
                env=environ | dict(environment_variables),
                **(dict(editor=editor) if editor else {}),
            )
    else:
        oreo.cprint(ctx.obj.tailnet.policy)


@main.command()
@click.pass_context
def summary(ctx):
    oreo.cprint(ctx.obj.tailnet)
