{ pkgs ? import <nixpkgs> {} }:
  pkgs.mkShell {
    nativeBuildInputs = (with pkgs.gst_all_1; [
      gstreamer
      gst-plugins-base
      gst-plugins-good
      gst-plugins-bad
      gst-plugins-ugly
      gst-plugins-rs
    ]) ++ (with pkgs.python3Packages; [
      pygobject3
      websockets
      gst-python
    ]) ++ (with pkgs; [
      glib-networking
      gobject-introspection
      libnice
      python3
      wrapGAppsHook
      yt-dlp

      nodejs
    ]);

    # https://nixos.wiki/wiki/Development_environment_with_nix-shell
    shellHook = with pkgs; ''
      export GIO_EXTRA_MODULES=${pkgs.glib-networking}/lib/gio/modules
    '';
}
