
package us.kbase.readsutils;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.annotation.Generated;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * <p>Original spec-file type: ConvertReadLibraryParams</p>
 * <pre>
 * Input parameters for converting libraries to files.
 * list<read_lib> read_libraries - the names of the workspace read library
 *     objects to convert.
 * tern gzip - if true, gzip any unzipped files. If false, gunzip any
 *     zipped files. If null or missing, leave files as is unless
 *     unzipping is required for interleaving or deinterleaving, in which
 *     case the files will be left unzipped.
 * tern interleaved - if true, provide the files in interleaved format if
 *     they are not already. If false, provide forward and reverse reads
 *     files. If null or missing, leave files as is.
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "read_libraries",
    "gzip",
    "interleaved"
})
public class ConvertReadLibraryParams {

    @JsonProperty("read_libraries")
    private List<String> readLibraries;
    @JsonProperty("gzip")
    private java.lang.String gzip;
    @JsonProperty("interleaved")
    private java.lang.String interleaved;
    private Map<java.lang.String, Object> additionalProperties = new HashMap<java.lang.String, Object>();

    @JsonProperty("read_libraries")
    public List<String> getReadLibraries() {
        return readLibraries;
    }

    @JsonProperty("read_libraries")
    public void setReadLibraries(List<String> readLibraries) {
        this.readLibraries = readLibraries;
    }

    public ConvertReadLibraryParams withReadLibraries(List<String> readLibraries) {
        this.readLibraries = readLibraries;
        return this;
    }

    @JsonProperty("gzip")
    public java.lang.String getGzip() {
        return gzip;
    }

    @JsonProperty("gzip")
    public void setGzip(java.lang.String gzip) {
        this.gzip = gzip;
    }

    public ConvertReadLibraryParams withGzip(java.lang.String gzip) {
        this.gzip = gzip;
        return this;
    }

    @JsonProperty("interleaved")
    public java.lang.String getInterleaved() {
        return interleaved;
    }

    @JsonProperty("interleaved")
    public void setInterleaved(java.lang.String interleaved) {
        this.interleaved = interleaved;
    }

    public ConvertReadLibraryParams withInterleaved(java.lang.String interleaved) {
        this.interleaved = interleaved;
        return this;
    }

    @JsonAnyGetter
    public Map<java.lang.String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(java.lang.String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public java.lang.String toString() {
        return ((((((((("ConvertReadLibraryParams"+" [readLibraries=")+ readLibraries)+", gzip=")+ gzip)+", interleaved=")+ interleaved)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
