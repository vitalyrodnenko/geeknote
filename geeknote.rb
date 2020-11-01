class Geeknote < Formula
  homepage 'http://www.geeknote.me/'
  head 'https://github.com/VitaliyRodnenko/geeknote'

  depends_on :python

  def install
    ENV["PYTHONPATH"] = libexec/"vendor/lib/python2.7/site-packages"
    ENV.prepend_create_path "PYTHONPATH", lib+"python2.7/site-packages"

    system "python", "setup.py", "install", "--prefix=#{prefix}"

    bin.env_script_all_files(libexec/"bin", :PYTHONPATH => ENV["PYTHONPATH"])
  end
end
