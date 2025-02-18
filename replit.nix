{pkgs}: {
  deps = [
    pkgs.cairo
    pkgs.pango
    pkgs.xorg.libXfixes
    pkgs.xorg.libXdamage
    pkgs.xorg.libXcomposite
    pkgs.xorg.libxcb
    pkgs.at-spi2-core
    pkgs.cups
    pkgs.alsa-lib
    pkgs.nss
    pkgs.gtk3
    pkgs.chromium
    pkgs.playwright-driver
    pkgs.gitFull
    pkgs.postgresql
    pkgs.openssl
  ];
}
