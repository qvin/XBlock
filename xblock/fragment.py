"""Fragments for XBlocks.

This code is in the Runtime layer.

"""

from collections import namedtuple
from hashlib import md5

from xblock.utils import OrderedSet

# pylint: disable=C0103
_FRTuple = namedtuple("_FragmentResource", "kind, data, mimetype, placement")

class _FragmentResource(_FRTuple):

    __slots__ = ()

    def __repr__(self):
        instance_str = "_FragmentResource(kind=%r,data=%,mimetype=%r,placement=%r)"

        return instance_str % (self.kind, self.data, self.mimetype,
                self.placement)

    def __str__(self):
        """ Returns `resource` wrapped in the appropriate html tag for it's
        mimetype.
        """
        if self.mimetype == "text/css":
            if self.kind == "text":
                return (u"<style type='text/css'>\n%s\n</style>" % self.data)
            elif self.kind == "url":
                return (u"<link rel='stylesheet' href='%s' type='text/css'>" % self.data)

        elif self.mimetype == "application/javascript":
            if self.kind == "text":
                return (u"<script>\n%s\n</script>" % self.data)
            elif kind == "url":
                return (u"<script src='%s' type='application/javascript'></script>" % self.data)

        elif self.mimetype == "text/html":
            assert self.kind == "text"
            return self.data

        else:
            raise Exception("Never heard of mimetype %r" % mimetype)

    @property
    def _undigested_hash(self):
        """ An 'undigested' hash for this object. Useful for hashing multiple
        `_FragmentResource` objects together.
        """
        h = md5()
        h.update(self.kind)
        h.update(self.data)
        h.update(self.mimetype)
        h.update(self.placement)
        return h


    def __hash__(self):
        """ Hash based on fragment's fields"""
        return int(self._undigested_hash.hexdigest(), 16)

    def __eq__(self, other):
        return (isinstance(other, _FragmentResource) and
            self.__hash__() == hash(other))


class Fragment(object):
    """A fragment of a web page, for XBlock views to return.

    A fragment consists of HTML for the body of the page, and a series of
    resources needed by the body. Resources are specified with a MIME type
    (such as "application/javascript" or "text/css") that determines how they
    are inserted into the page.  The resource is provided either as literal
    text, or as a URL.  Text will be included on the page, wrapped
    appropriately for the MIME type.  URLs will be used as-is on the page.

    Resources are only inserted into the page once, even if many Fragments
    in the page ask for them.  Determining duplicates is done by simple text
    matching.

    """
    def __init__(self, content=None):
        self.content = u""
        self.resources = OrderedSet()
        self.js_init = None

        if content is not None:
            self.add_content(content)

    def to_pods(self):
        """Returns the data in a dictionary.

        'pods' = Plain Old Data Structure."""
        return {
            'content': self.content,
            'resources': [dict(r) for r in self.resources],
            'js_init': self.js_init
        }

    @classmethod
    def from_pods(cls, pods):
        """
        Returns a new Fragment from a `pods`.

        `pods` is a Plain Old Data Structure, a Python dictionary with
        keys `content`, `resources`, and `js_init`

        """
        frag = cls()
        frag.content = pods['content']
        frag.resources = OrderedSet([_FragmentResource(**d) for d in
            pods['resources']])
        frag.js_init = pods['js_init']
        return frag

    def add_content(self, content):
        """Add content to this fragment.

        `content` is a Unicode string, HTML to append to the body of the
        fragment.  It must not contain a ``<body>`` tag, or otherwise assume
        that it is the only content on the page.

        """
        assert isinstance(content, unicode)
        self.content += content

    def _default_placement(self, mimetype):
        """Decide where a resource will go, if the user didn't say."""
        if mimetype == 'application/javascript':
            return 'foot'
        return 'head'

    def add_resource(self, text, mimetype, placement=None):
        """Add a resource needed by this Fragment.

        Other helpers, such as :func:`add_css` or :func:`add_javascript` are
        more convenient for those common types of resource.

        `text`: the actual text of this resource, as a unicode string.

        `mimetype`: the MIME type of the resource.

        `placement`: where on the page the resource should be placed:

            None: let the Fragment choose based on the MIME type.

            "head": put this resource in the ``<head>`` of the page.

            "foot": put this resource at the end of the ``<body>`` of the
            page.

        """
        if not placement:
            placement = self._default_placement(mimetype)
        res = _FragmentResource('text', text, mimetype, placement)
        self.resources.add(res)

    def add_resource_url(self, url, mimetype, placement=None):
        """Add a resource by URL needed by this Fragment.

        Other helpers, such as :func:`add_css_url` or
        :func:`add_javascript_url` are more convenent for those common types of
        resource.

        `url`: the URL to the resource.

        Other parameters are as defined for :func:`add_resource`.

        """
        if not placement:
            placement = self._default_placement(mimetype)
        self.resources.add(_FragmentResource('url', url, mimetype, placement))

    def add_css(self, text):
        """Add literal CSS to the Fragment."""
        self.add_resource(text, 'text/css')

    def add_css_url(self, url):
        """Add a CSS URL to the Fragment."""
        self.add_resource_url(url, 'text/css')

    def add_javascript(self, text):
        """Add literal Javascript to the Fragment."""
        self.add_resource(text, 'application/javascript')

    def add_javascript_url(self, url):
        """Add a Javascript URL to the Fragment."""
        self.add_resource_url(url, 'application/javascript')

    def add_frag_resources(self, frag):
        """Add all the resources from `frag` to my resources.

        This is used by an XBlock to collect resources from Fragments produced
        by its children.

        `frag` is a Fragment.

        The content from the Fragment is ignored.  The caller must collect
        together the content into this Fragment's content.

        """
        self.resources.union(frag.resources)

    def add_frags_resources(self, frags):
        """Add all the resources from `frags` to my resources.

        This is used by an XBlock to collect resources from Fragments produced
        by its children.

        `frags` is a sequence of Fragments.

        The content from the Fragments is ignored.  The caller must collect
        together the content into this Fragment's content.

        """
        for resource in frags:
            self.add_frag_resources(resource)

    def initialize_js(self, js_func):
        """Register a Javascript function to initialize the Javascript resources.

        `js_func` is the name of a Javascript function defined by one of the
        Javascript resources.  As part of setting up the browser's runtime
        environment, the function will be invoked, passing a runtime object
        and a DOM element.

        """
        # This is version 1 of the interface.
        self.js_init = (js_func, 1)

    # Implementation methods: don't override
    # TODO: [rocha] should this go in the runtime?

    def body_html(self):
        """Get the body HTML for this Fragment.

        Returns a Unicode string, the HTML content for the ``<body>`` section
        of the page.

        """
        return self.content

    def head_html(self):
        """Get the head HTML for this Fragment.

        Returns a Unicode string, the HTML content for the ``<head>`` section
        of the page.

        """
        return self._resource_html("head")

    def foot_html(self):
        """Get the foot HTML for this Fragment.

        Returns a Unicode string, the HTML content for the end of the
        ``<body>`` section of the page.

        """
        return self._resource_html("foot")

    def _resource_html(self, placement):
        """Get some resource HTML for this Fragment.

        `placement` is "head" or "foot".

        Returns a unicode string, the HTML for the head or foot of the page.

        """
        # The list of HTML to return
        html = ""

        # TODO: [rocha] aggregate and wrap css and javascript.
        # - non url js could be wrapped in an anonymous function
        # - non url css could be rewritten to match the wrapper tag

        for resource in self.resources:
            # Only take the pieces for our placement.
            if resource.placement != placement:
                continue
            html += (str(resource) + "\n")

        return html
