
#ifndef THIRD_PARTY
#define THIRD_PARTY

#include <zlib.h>
#include <string>
#include <cstring>
#include <stdexcept>
#include <sstream>
#include <ios>
#include <fstream>
#include <iostream>
#if __cplusplus >= 201703L
#include <string_view>
#endif  // __cplusplus >= 201703L
//base64
std::string base64_encode     (std::string const& s, bool url = false);
std::string base64_encode_pem (std::string const& s);
std::string base64_encode_mime(std::string const& s);

std::string base64_decode(std::string const& s, bool remove_linebreaks = false);
std::string base64_encode(unsigned char const*, size_t len, bool url = false);
//zlib
std::string zlibencode(const std::string& str, int compressionlevel = Z_BEST_COMPRESSION);
std::string zlibdecode(const std::string& str);
//mem
void display_mem_usage();

#if __cplusplus >= 201703L
//
// Interface with std::string_view rather than const std::string&
// Requires C++17
// Provided by Yannic Bonenberger (https://github.com/Yannic)
//
std::string base64_encode     (std::string_view s, bool url = false);
std::string base64_encode_pem (std::string_view s);
std::string base64_encode_mime(std::string_view s);

std::string base64_decode(std::string_view s, bool remove_linebreaks = false);
#endif  // __cplusplus >= 201703L

#endif /* THIRD_PARTY */
